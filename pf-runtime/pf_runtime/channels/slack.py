"""Slack channel adapter — Socket Mode, DM-only, personal-profile.

Sub-phase 4.7.3 (throwaway) scope:
    - Socket Mode WebSocket via slack-bolt AsyncApp + AsyncSocketModeHandler.
    - Direct Messages (channel_type == "im") only — channel/thread/group DMs
      are silently dropped. No slash commands, no file uploads, no approval
      buttons (those land post-cutover).
    - In-memory LRU dedup for inbound (event_id) and outbound (message_id),
      bounded at ``dedup_window`` (default 10K).
    - Reconnect is the gateway's job — this adapter raises ChannelConnectError
      / ChannelError on transport failure and lets the gateway's epoch loop
      decide whether to retry.

Tokens are loaded from the profile's ``.env`` via ``_load_dotenv`` (NOT from
``os.environ``) so each profile uses its own Slack app credentials and the
adapter never poisons the process env.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from pf_runtime.channels.adapter_base import (
    Channel,
    ChannelAuthError,
    ChannelConnectError,
    ChannelError,
    ChannelMessageTooLarge,
    ChannelRateLimited,
)
from pf_runtime.config import InboundMessage, OutboundMessage
from pf_runtime.runtime.model_adapter import _load_dotenv

# slack-bolt is an optional dependency declared under the [channels] extra.
# Importing the module must not fail when slack-bolt is absent so that the
# rest of the package (and the test suite for non-Slack code) remains usable.
try:
    from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
    from slack_bolt.async_app import AsyncApp
    from slack_sdk.errors import SlackApiError

    _SLACK_AVAILABLE = True
except ImportError:  # pragma: no cover — exercised only when extra not installed
    AsyncApp = None  # type: ignore[assignment,misc]
    AsyncSocketModeHandler = None  # type: ignore[assignment,misc]
    SlackApiError = Exception  # type: ignore[assignment,misc]
    _SLACK_AVAILABLE = False


_log = logging.getLogger(__name__)


# Slack errors that mean "credentials are bad — don't retry".
_AUTH_ERROR_CODES: frozenset[str] = frozenset(
    {"invalid_auth", "not_authed", "token_revoked", "account_inactive"}
)


class SlackChannel(Channel):
    """Slack Socket Mode adapter — DM-only, in-memory dedup."""

    name: str = "slack"

    def __init__(
        self,
        profile_slug: str,
        env_path: Path,
        *,
        dedup_window: int = 10000,
    ) -> None:
        # Instance attributes shadow the class-level attribute declarations
        # on the ABC; this is intentional so subclasses can carry state.
        self.name = "slack"
        self.profile_slug = profile_slug

        env = _load_dotenv(env_path)
        bot_token = env.get("SLACK_BOT_TOKEN", "")
        app_token = env.get("SLACK_APP_TOKEN", "")
        if not bot_token:
            raise ChannelAuthError(f"SLACK_BOT_TOKEN missing in {env_path}")
        if not app_token:
            raise ChannelAuthError(f"SLACK_APP_TOKEN missing in {env_path}")
        self._bot_token: str = bot_token
        self._app_token: str = app_token

        self._app: Any | None = None
        self._handler: Any | None = None
        self._socket_mode_task: asyncio.Task[None] | None = None

        self._inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._inbound_dedup: OrderedDict[str, None] = OrderedDict()
        self._outbound_dedup: OrderedDict[str, None] = OrderedDict()
        self._dedup_window: int = dedup_window

        self._bot_user_id: str | None = None
        self._connected: bool = False
        # U… → D… DM channel id cache; populated lazily on first send to a user.
        self._dm_channel_cache: dict[str, str] = {}
        self._thread_roots_path = (
            env_path.parent / "runtime-state" / "slack-conversations.json"
        )
        self._thread_roots: dict[str, str] = self._load_thread_roots()

    # ------------------------------------------------------------------ #
    # Connect / disconnect
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """Open the Socket Mode WebSocket; idempotent on re-call."""
        # Idempotent guard: if we're already connected and the socket task
        # is still running, do nothing.
        if (
            self._connected
            and self._handler is not None
            and self._socket_mode_task is not None
            and not self._socket_mode_task.done()
        ):
            return

        if not _SLACK_AVAILABLE:
            raise ChannelConnectError(
                "slack-bolt not installed; run: pip install 'pf-runtime[channels]'"
            )

        # If we're reconnecting after a fault, tear down stale state first.
        if self._handler is not None:
            # Best-effort cleanup of stale handler — exceptions during
            # teardown are not actionable and would mask the reconnect.
            with contextlib.suppress(Exception):
                await self._handler.close_async()
            self._handler = None
            self._app = None

        try:
            app = AsyncApp(token=self._bot_token)

            # Pre-flight auth call — fast-fail on bad credentials before we
            # spin up the long-running socket task.
            try:
                auth = await app.client.auth_test()
            except SlackApiError as e:
                err = e.response.get("error", "") if hasattr(e, "response") else ""
                if err in _AUTH_ERROR_CODES:
                    raise ChannelAuthError(f"Slack auth failed: {err}") from e
                raise

            self._bot_user_id = auth["user_id"]

            # Wire event handlers.
            @app.event("message")
            async def _handle_message(event: dict[str, Any]) -> None:
                await self._on_slack_message(event)

            # No-op handlers — without these slack-bolt logs unhandled-request
            # warnings every time Slack mirrors these events (and Slack's app
            # config sometimes mirrors @mentions to app_mention).
            @app.event("app_mention")
            async def _handle_app_mention(event: dict[str, Any]) -> None:
                return

            @app.event("file_shared")
            async def _handle_file_shared(event: dict[str, Any]) -> None:
                return

            @app.event("file_created")
            async def _handle_file_created(event: dict[str, Any]) -> None:
                return

            @app.event("file_change")
            async def _handle_file_change(event: dict[str, Any]) -> None:
                return

            @app.event("assistant_thread_started")
            async def _handle_thread_started(event: dict[str, Any]) -> None:
                return

            @app.event("assistant_thread_context_changed")
            async def _handle_thread_context(event: dict[str, Any]) -> None:
                return

            self._app = app

            handler: Any = AsyncSocketModeHandler(app, self._app_token)
            self._handler = handler
            self._socket_mode_task = asyncio.create_task(handler.start_async())

            # Yield once so any synchronous startup error inside start_async
            # surfaces here instead of silently in the background task.
            await asyncio.sleep(0.1)

            if self._socket_mode_task.done():
                exc = self._socket_mode_task.exception()
                raise ChannelConnectError(
                    f"Socket Mode task exited during startup: {exc}"
                )

            self._connected = True
            _log.info(
                "[SlackChannel] connected as bot=%s profile=%s",
                self._bot_user_id,
                self.profile_slug,
            )

        except ChannelError:
            # Already a typed channel error — propagate as-is.
            self._connected = False
            raise
        except SlackApiError as e:
            self._connected = False
            err = e.response.get("error", "") if hasattr(e, "response") else ""
            if err in _AUTH_ERROR_CODES:
                raise ChannelAuthError(f"Slack auth failed: {err}") from e
            raise ChannelConnectError(f"Slack connect failed: {err or e}") from e
        except Exception as e:
            self._connected = False
            raise ChannelConnectError(f"Slack connect failed: {e}") from e

    async def disconnect(self) -> None:
        """Best-effort shutdown — never raises."""
        if self._handler is not None:
            try:
                await self._handler.close_async()
            except Exception as e:
                _log.warning("Slack disconnect (handler.close_async): %s", e)

        if self._socket_mode_task is not None and not self._socket_mode_task.done():
            self._socket_mode_task.cancel()
            try:
                await self._socket_mode_task
            except (asyncio.CancelledError, Exception) as e:
                if not isinstance(e, asyncio.CancelledError):
                    _log.warning("Slack disconnect (socket task): %s", e)

        self._connected = False
        self._handler = None
        self._app = None
        self._socket_mode_task = None

    # ------------------------------------------------------------------ #
    # Inbound — Socket Mode handler & async iterator
    # ------------------------------------------------------------------ #

    async def _on_slack_message(self, event: dict[str, Any]) -> None:
        """Bolt event handler — filters DMs, dedups, and queues InboundMessage."""
        event_id = (
            event.get("event_id") or event.get("client_msg_id") or event.get("ts")
        )
        if not event_id:
            return

        # DM-only in throwaway. Channels, threads, group DMs are deferred.
        if event.get("channel_type") != "im":
            return

        # Skip ourselves and any non-user messages (bot_message, edits, etc.).
        if event.get("user") == self._bot_user_id:
            return
        if event.get("subtype"):
            return

        # Inbound LRU dedup — Slack occasionally redelivers events on
        # reconnect; we never want to enqueue the same one twice.
        if event_id in self._inbound_dedup:
            return
        self._inbound_dedup[event_id] = None
        while len(self._inbound_dedup) > self._dedup_window:
            self._inbound_dedup.popitem(last=False)

        thread_ts = self._conversation_thread_ts(event)
        msg = InboundMessage(
            channel="slack",
            profile_slug=self.profile_slug,
            user_id=event["user"],
            text=event.get("text", ""),
            message_id=event_id,
            metadata={
                "channel_id": event["channel"],
                "ts": event["ts"],
                # One stable App Home thread per Slack user + bot. Slack's
                # Chat tab otherwise treats each top-level exchange as a
                # separate History item, which feels broken for a bot DM.
                "thread_ts": thread_ts,
                "team": event.get("team", ""),
            },
        )
        await self._inbound_queue.put(msg)

    def _conversation_key(self, event: dict[str, Any]) -> str:
        team = event.get("team") or ""
        return f"{team}:{event['channel']}:{event['user']}"

    def _conversation_thread_ts(self, event: dict[str, Any]) -> str:
        key = self._conversation_key(event)
        existing = self._thread_roots.get(key)
        if existing:
            return existing

        thread_ts = str(event.get("thread_ts") or event["ts"])
        self._thread_roots[key] = thread_ts
        self._save_thread_roots()
        return thread_ts

    def _load_thread_roots(self) -> dict[str, str]:
        try:
            raw = json.loads(self._thread_roots_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        if not isinstance(raw, dict):
            return {}
        return {str(k): str(v) for k, v in raw.items() if isinstance(v, str)}

    def _save_thread_roots(self) -> None:
        try:
            self._thread_roots_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._thread_roots_path.with_suffix(".json.tmp")
            tmp.write_text(
                json.dumps(self._thread_roots, sort_keys=True, indent=2),
                encoding="utf-8",
            )
            tmp.replace(self._thread_roots_path)
        except OSError as e:
            _log.warning("could not persist Slack conversation roots: %s", e)

    async def receive(self) -> AsyncIterator[InboundMessage]:
        """Yield queued inbound messages indefinitely.

        The caller breaks the loop by cancelling the task that is iterating
        over this generator (the gateway's consume task does this on
        shutdown).
        """
        while True:
            msg = await self._inbound_queue.get()
            yield msg

    # ------------------------------------------------------------------ #
    # Outbound — chat.postMessage with idempotency on message_id
    # ------------------------------------------------------------------ #

    async def send(self, msg: OutboundMessage) -> None:
        """Send a chat.postMessage; idempotent on ``msg.message_id``."""
        mid = msg.message_id or f"slack-out-{uuid.uuid4()}"
        # Outbound dedup — check BEFORE sending so retries after a transient
        # failure can re-send (we only record on success below).
        if mid in self._outbound_dedup:
            return

        if self._app is None:
            raise ChannelError("Slack channel is not connected")

        # Resolve target channel id.
        target = msg.target_user_id
        channel_id: str
        if target.startswith(("D", "C")):
            # Already a channel id (DM or public channel).
            channel_id = target
        elif target.startswith("U"):
            cached = self._dm_channel_cache.get(target)
            if cached is not None:
                channel_id = cached
            else:
                try:
                    resp = await self._app.client.conversations_open(users=target)
                except SlackApiError as e:
                    err = e.response.get("error", "") if hasattr(e, "response") else ""
                    if err in _AUTH_ERROR_CODES:
                        raise ChannelAuthError(err) from e
                    raise ChannelError(f"Slack conversations.open failed: {err}") from e
                channel_id = resp["channel"]["id"]
                self._dm_channel_cache[target] = channel_id
        else:
            # Unknown prefix — trust the caller.
            channel_id = target

        post_kwargs: dict[str, Any] = {
            "channel": channel_id,
            "text": msg.text,
        }
        thread_ts = msg.metadata.get("thread_ts")
        if thread_ts:
            post_kwargs["thread_ts"] = thread_ts

        try:
            await self._app.client.chat_postMessage(**post_kwargs)
        except SlackApiError as e:
            err = e.response.get("error", "") if hasattr(e, "response") else ""
            if err == "ratelimited":
                retry_after_raw = 30
                # Headers may be a dict-like or a Mapping; tolerate both.
                headers = getattr(e.response, "headers", None)
                if headers is not None:
                    try:
                        retry_after_raw = int(headers.get("Retry-After", 30))
                    except (TypeError, ValueError):
                        retry_after_raw = 30
                raise ChannelRateLimited(
                    "rate limited", retry_after_seconds=retry_after_raw
                ) from e
            if err == "msg_too_long":
                raise ChannelMessageTooLarge(err) from e
            if err in _AUTH_ERROR_CODES:
                raise ChannelAuthError(err) from e
            raise ChannelError(f"Slack API error: {err}") from e

        # Record dedup AFTER successful upstream call — transient failures
        # remain retryable.
        self._outbound_dedup[mid] = None
        while len(self._outbound_dedup) > self._dedup_window:
            self._outbound_dedup.popitem(last=False)

    # ------------------------------------------------------------------ #
    # No-op channel hooks
    # ------------------------------------------------------------------ #

    async def typing(self, target_user_id: str, on: bool) -> None:
        """Slack bot DMs lack a native typing indicator outside the AI
        Assistant API; we don't use that surface in throwaway."""
        return

    async def ack(self, message_id: str) -> None:
        """Socket Mode acks at the transport layer; nothing to do here."""
        return
