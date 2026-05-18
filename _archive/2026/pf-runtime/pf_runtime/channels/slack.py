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
import urllib.error
import urllib.request
import uuid
from collections import OrderedDict
from collections.abc import AsyncIterator
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

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
if TYPE_CHECKING:  # pragma: no branch
    from slack_bolt.adapter.socket_mode.async_handler import (
        AsyncSocketModeHandler as _AsyncSocketModeHandler,
    )
    from slack_bolt.async_app import AsyncApp as _AsyncApp
    from slack_sdk.errors import SlackApiError as _SlackApiError

    AsyncApp = _AsyncApp
    AsyncSocketModeHandler = _AsyncSocketModeHandler
    SlackApiError = _SlackApiError
    _SLACK_AVAILABLE = True
else:
    try:
        from slack_bolt.adapter.socket_mode.async_handler import (
            AsyncSocketModeHandler as _AsyncSocketModeHandler,
        )
        from slack_bolt.async_app import AsyncApp as _AsyncApp
        from slack_sdk.errors import SlackApiError as _SlackApiError

        AsyncApp = _AsyncApp
        AsyncSocketModeHandler = _AsyncSocketModeHandler
        SlackApiError = _SlackApiError
        _SLACK_AVAILABLE = True
    except ImportError:  # pragma: no cover — exercised only when extra not installed
        _SLACK_AVAILABLE = False
        AsyncApp = Any  # type: ignore[assignment,misc]
        AsyncSocketModeHandler = Any  # type: ignore[assignment,misc]
        SlackApiError = Exception


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
        inbound_ledger: Any | None = None,
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
        self._pfos_base_url: str = env.get("PFOS_BASE_URL", "").rstrip("/")
        self._atlas_decide_token: str = env.get("PFOS_ATLAS_DECIDE_TOKEN", "")

        self._app: Any | None = None
        self._handler: Any | None = None
        self._socket_mode_task: asyncio.Task[None] | None = None

        self._inbound_queue: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self._inbound_dedup: OrderedDict[str, None] = OrderedDict()
        self._outbound_dedup: OrderedDict[str, None] = OrderedDict()
        self._dedup_window: int = dedup_window
        self._inbound_ledger: Any | None = inbound_ledger

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

            @app.action("atlas_decision_approve")
            async def _handle_atlas_approve(ack: Any, body: dict[str, Any]) -> None:
                await ack()
                await self._on_atlas_decision_action(body, "approve")

            @app.action("atlas_decision_reject")
            async def _handle_atlas_reject(ack: Any, body: dict[str, Any]) -> None:
                await ack()
                await self._on_atlas_decision_action(body, "reject")

            @app.action("atlas_decision_open_pfos")
            async def _handle_atlas_open_pfos(ack: Any, body: dict[str, Any]) -> None:
                del body
                await ack()

            @app.view("atlas_decision_feedback")
            async def _handle_atlas_feedback_view(
                ack: Any, body: dict[str, Any]
            ) -> None:
                await ack()
                await self._on_atlas_decision_feedback_submission(body)

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
        if self._inbound_ledger is not None:
            claimed = await asyncio.to_thread(self._inbound_ledger.try_claim, event_id)
            if not claimed:
                return
        elif event_id in self._inbound_dedup:
            return
        if self._inbound_ledger is None:
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
        out_key = (
            f"{self.profile_slug}:{msg.in_reply_to}" if msg.in_reply_to else None
        )
        if (
            self._inbound_ledger is not None
            and out_key
            and await asyncio.to_thread(
                self._inbound_ledger.outbound_already_sent,
                out_key,
            )
        ):
            return
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
        blocks = msg.metadata.get("blocks")
        if isinstance(blocks, list):
            post_kwargs["blocks"] = blocks

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
        if self._inbound_ledger is not None and out_key:
            await asyncio.to_thread(self._inbound_ledger.record_outbound_sent, out_key)
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

    async def _on_atlas_decision_action(
        self,
        body: dict[str, Any],
        verdict: str,
    ) -> None:
        """Open a small feedback modal before resolving an Atlas proposal."""
        if self._app is None:
            return
        value = _first_action_value(body)
        action_id = str(value.get("action_id") or "").strip()
        silo_slug = str(value.get("silo_slug") or "prettyfly").strip()
        slack_user_id = str((body.get("user") or {}).get("id") or "").strip()
        channel_id = _slack_action_channel_id(body)
        message_ts = _slack_action_message_ts(body)

        if not action_id or not channel_id or not message_ts:
            return

        if not self._pfos_base_url or not self._atlas_decide_token:
            await self._update_atlas_decision_message(
                channel_id=channel_id,
                message_ts=message_ts,
                text="Atlas decision could not be recorded: PFOS decide token is not configured.",
            )
            return

        trigger_id = str(body.get("trigger_id") or "").strip()
        if not trigger_id:
            await self._update_atlas_decision_message(
                channel_id=channel_id,
                message_ts=message_ts,
                text="Atlas decision could not be recorded: Slack did not provide a modal trigger.",
            )
            return

        try:
            await self._app.client.views_open(
                trigger_id=trigger_id,
                view=atlas_decision_feedback_modal(
                    action_id=action_id,
                    silo_slug=silo_slug,
                    verdict=verdict,
                    channel_id=channel_id,
                    message_ts=message_ts,
                    slack_user_id=slack_user_id,
                ),
            )
        except SlackApiError as e:
            err = e.response.get("error", "") if hasattr(e, "response") else ""
            await self._update_atlas_decision_message(
                channel_id=channel_id,
                message_ts=message_ts,
                text=f"Atlas decision feedback modal could not open: {err or e}.",
            )

    async def _on_atlas_decision_feedback_submission(
        self,
        body: dict[str, Any],
    ) -> None:
        """Resolve Atlas decision feedback modal through PFOS, then update Slack."""
        if self._app is None:
            return
        metadata = _view_private_metadata(body)
        action_id = str(metadata.get("action_id") or "").strip()
        silo_slug = str(metadata.get("silo_slug") or "prettyfly").strip()
        verdict = str(metadata.get("verdict") or "").strip()
        slack_user_id = str(metadata.get("slack_user_id") or "").strip()
        channel_id = str(metadata.get("channel_id") or "").strip()
        message_ts = str(metadata.get("message_ts") or "").strip()
        feedback_code = _view_feedback_code(body)
        feedback_note = _view_feedback_note(body)

        if verdict not in {"approve", "reject"} or not action_id:
            return
        if not channel_id or not message_ts:
            return
        if not self._pfos_base_url or not self._atlas_decide_token:
            await self._update_atlas_decision_message(
                channel_id=channel_id,
                message_ts=message_ts,
                text="Atlas decision could not be recorded: PFOS decide token is not configured.",
            )
            return

        result = await _patch_pfos_decision(
            base_url=self._pfos_base_url,
            token=self._atlas_decide_token,
            silo_slug=silo_slug,
            action_id=action_id,
            verdict=verdict,
            slack_user_id=slack_user_id,
            feedback_code=feedback_code,
            feedback_note=feedback_note,
        )
        status = str(result.get("status") or result.get("current_status") or "")
        if result.get("ok") is True:
            feedback_label = _atlas_feedback_label(feedback_code)
            text = (
                f"Atlas proposal {status}. Feedback: {feedback_label}. "
                "Decision recorded; no execution was triggered."
            )
            follow_up_event_id = str(result.get("follow_up_event_id") or "").strip()
            if verdict == "approve" and follow_up_event_id:
                await self._enqueue_atlas_follow_up(
                    channel_id=channel_id,
                    message_ts=message_ts,
                    slack_user_id=slack_user_id,
                    source_action_id=action_id,
                    follow_up_event_id=follow_up_event_id,
                )
        elif result.get("error") == "already_resolved" and status:
            text = f"Atlas proposal was already {status}. No execution was triggered."
        else:
            text = f"Atlas decision could not be recorded: {result.get('error', 'unknown_error')}."

        await self._update_atlas_decision_message(
            channel_id=channel_id,
            message_ts=message_ts,
            text=text,
        )

    async def _enqueue_atlas_follow_up(
        self,
        *,
        channel_id: str,
        message_ts: str,
        slack_user_id: str,
        source_action_id: str,
        follow_up_event_id: str,
    ) -> None:
        msg = InboundMessage(
            channel="slack",
            profile_slug=self.profile_slug,
            user_id=slack_user_id,
            text=(
                "Approved decision follow-up requested. Use the verified "
                f"source packet for atlas.follow_up.queued event {follow_up_event_id} "
                f"and source action {source_action_id}. Produce the five-field "
                "follow-up brief and record atlas.follow_up.ready. Do not execute, "
                "dispatch, send externally, create tasks, spend, deploy, or edit files."
            ),
            message_id=f"atlas-follow-up-{follow_up_event_id}",
            metadata={
                "channel_id": channel_id,
                "ts": message_ts,
                "thread_ts": message_ts,
                "synthetic": "atlas_approval_follow_up",
                "atlas_follow_up_event_id": follow_up_event_id,
                "atlas_source_action_id": source_action_id,
            },
        )
        await self._inbound_queue.put(msg)

    async def _update_atlas_decision_message(
        self,
        *,
        channel_id: str,
        message_ts: str,
        text: str,
    ) -> None:
        if self._app is None:
            return
        blocks = [
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text},
            }
        ]
        try:
            await self._app.client.chat_update(
                channel=channel_id,
                ts=message_ts,
                text=text,
                blocks=blocks,
            )
        except SlackApiError as e:
            err = e.response.get("error", "") if hasattr(e, "response") else ""
            _log.warning("Slack atlas decision update failed: %s", err or e)


ATLAS_FEEDBACK_OPTIONS: tuple[tuple[str, str], ...] = (
    ("good_call", "Good call"),
    ("wrong_priority", "Wrong priority"),
    ("missing_context", "Missing context"),
    ("too_vague", "Too vague"),
    ("too_risky", "Too risky"),
    ("not_now", "Not now"),
    ("needs_revision", "Needs revision"),
    ("other", "Other"),
)


def atlas_decision_feedback_modal(
    *,
    action_id: str,
    silo_slug: str,
    verdict: str,
    channel_id: str,
    message_ts: str,
    slack_user_id: str,
) -> dict[str, Any]:
    """Build the Slack feedback modal for Atlas approve/reject decisions."""
    default_code = "good_call" if verdict == "approve" else "needs_revision"
    metadata = {
        "action_id": action_id,
        "silo_slug": silo_slug,
        "verdict": verdict,
        "channel_id": channel_id,
        "message_ts": message_ts,
        "slack_user_id": slack_user_id,
    }
    options = [
        {
            "text": {"type": "plain_text", "text": label},
            "value": code,
        }
        for code, label in ATLAS_FEEDBACK_OPTIONS
    ]
    initial_option = next(
        option for option in options if option["value"] == default_code
    )
    title = "Approve Atlas?" if verdict == "approve" else "Reject Atlas?"
    return {
        "type": "modal",
        "callback_id": "atlas_decision_feedback",
        "private_metadata": json.dumps(metadata, separators=(",", ":")),
        "title": {"type": "plain_text", "text": title},
        "submit": {"type": "plain_text", "text": "Record"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "feedback_code",
                "label": {"type": "plain_text", "text": "Feedback"},
                "element": {
                    "type": "static_select",
                    "action_id": "feedback_code",
                    "options": options,
                    "initial_option": initial_option,
                },
            },
            {
                "type": "input",
                "block_id": "feedback_note",
                "optional": True,
                "label": {"type": "plain_text", "text": "Optional note"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "feedback_note",
                    "multiline": True,
                    "max_length": 500,
                },
            },
        ],
    }


def atlas_decision_card_blocks(card: dict[str, Any], *, base_url: str = "") -> list[dict[str, Any]]:
    """Build a compact, safe Atlas approval card for Slack DMs."""
    action_id = str(card.get("action_id") or "").strip()
    silo_slug = str(card.get("silo_slug") or "prettyfly").strip()
    title = _truncate_slack_text(str(card.get("title") or "Atlas decision proposal"), 140)
    summary = _truncate_slack_text(
        str(card.get("summary") or "Atlas is asking for a decision."),
        220,
    )
    priority = _truncate_slack_text(str(card.get("priority") or "normal"), 32)
    risk = _truncate_slack_text(str(card.get("risk_level") or "medium"), 32)
    pfos_href = str(card.get("pfos_href") or "/agents/atlas-ceo")
    url = _internal_pfos_url(base_url, pfos_href)
    value = json.dumps(
        {"action_id": action_id, "silo_slug": silo_slug},
        separators=(",", ":"),
        sort_keys=True,
    )
    elements: list[dict[str, Any]] = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Approve"},
            "style": "primary",
            "action_id": "atlas_decision_approve",
            "value": value,
        },
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Reject"},
            "action_id": "atlas_decision_reject",
            "value": value,
        },
    ]
    if url:
        elements.append(
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Open PFOS"},
                "url": url,
                "action_id": "atlas_decision_open_pfos",
                "value": value,
            }
        )
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{title}*\n{summary}"},
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Priority: `{priority}` · Risk: `{risk}` · payload redacted",
                }
            ],
        },
        {"type": "actions", "elements": elements},
    ]


def _first_action_value(body: dict[str, Any]) -> dict[str, Any]:
    actions = body.get("actions")
    if not isinstance(actions, list) or not actions:
        return {}
    raw = actions[0].get("value") if isinstance(actions[0], dict) else None
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _slack_action_channel_id(body: dict[str, Any]) -> str:
    container = body.get("container")
    if isinstance(container, dict) and isinstance(container.get("channel_id"), str):
        return str(container["channel_id"])
    channel = body.get("channel")
    if isinstance(channel, dict) and isinstance(channel.get("id"), str):
        return str(channel["id"])
    return ""


def _slack_action_message_ts(body: dict[str, Any]) -> str:
    container = body.get("container")
    if isinstance(container, dict) and isinstance(container.get("message_ts"), str):
        return str(container["message_ts"])
    message = body.get("message")
    if isinstance(message, dict) and isinstance(message.get("ts"), str):
        return str(message["ts"])
    return ""


def _view_private_metadata(body: dict[str, Any]) -> dict[str, Any]:
    view = body.get("view")
    raw = view.get("private_metadata") if isinstance(view, dict) else None
    if not isinstance(raw, str):
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _view_state_values(body: dict[str, Any]) -> dict[str, Any]:
    view = body.get("view")
    state = view.get("state") if isinstance(view, dict) else None
    values = state.get("values") if isinstance(state, dict) else None
    return values if isinstance(values, dict) else {}


def _view_feedback_code(body: dict[str, Any]) -> str:
    values = _view_state_values(body)
    block = values.get("feedback_code")
    action = block.get("feedback_code") if isinstance(block, dict) else None
    selected = action.get("selected_option") if isinstance(action, dict) else None
    raw = selected.get("value") if isinstance(selected, dict) else None
    return raw if isinstance(raw, str) and _atlas_feedback_label(raw) else "other"


def _view_feedback_note(body: dict[str, Any]) -> str:
    values = _view_state_values(body)
    block = values.get("feedback_note")
    action = block.get("feedback_note") if isinstance(block, dict) else None
    raw = action.get("value") if isinstance(action, dict) else None
    if not isinstance(raw, str):
        return ""
    return " ".join(raw.split()).strip()[:500]


def _atlas_feedback_label(code: str) -> str:
    return dict(ATLAS_FEEDBACK_OPTIONS).get(code, "Other")


def _truncate_slack_text(value: str, limit: int) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else f"{text[: max(limit - 1, 0)]}…"


def _internal_pfos_url(base_url: str, href: str) -> str:
    if not base_url or not href.startswith("/") or href.startswith("//"):
        return ""
    return f"{base_url.rstrip('/')}{href}"


async def _patch_pfos_decision(
    *,
    base_url: str,
    token: str,
    silo_slug: str,
    action_id: str,
    verdict: str,
    slack_user_id: str,
    feedback_code: str = "",
    feedback_note: str = "",
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/api/silos/{silo_slug}/agent-action/{action_id}"
    _ensure_http_url(url)

    def _sync() -> dict[str, Any]:
        payload = {
            "verdict": verdict,
            "slack_user_id": slack_user_id,
        }
        if feedback_code:
            payload["feedback_code"] = feedback_code
        if feedback_note:
            payload["feedback_note"] = feedback_note
        body = json.dumps(
            payload,
            separators=(",", ":"),
        ).encode("utf-8")
        req = urllib.request.Request(  # noqa: S310
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="PATCH",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 # nosec B310
                return _read_json_response(resp)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"error": f"http_{exc.code}"}
            if isinstance(parsed, dict):
                parsed.setdefault("ok", False)
                return parsed
            return {"ok": False, "error": f"http_{exc.code}"}
        except urllib.error.URLError as exc:
            return {"ok": False, "error": str(exc.reason)}

    return await asyncio.to_thread(_sync)


def _ensure_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("PFOS URL must be http(s)")


def _read_json_response(resp: Any) -> dict[str, Any]:
    body = resp.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "error": "invalid_json"}
    return data if isinstance(data, dict) else {"ok": False, "error": "invalid_json"}
