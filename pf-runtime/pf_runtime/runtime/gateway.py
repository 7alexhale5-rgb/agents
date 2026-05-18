"""Long-running channel gateway daemon.

The gateway is the bridge between channel adapters (Slack, Telegram, …) and
the per-turn ``run_session`` primitive. Responsibilities:

    1. Build the model adapter + memory stack once at startup (shared across
       all inbound messages — no per-message reconstruction overhead).
    2. Connect each requested channel and spawn a consumer task that drives
       its ``receive()`` async iterator.
    3. Translate inbound → ``run_session`` → outbound.
    4. Survive transient channel faults via the per-channel reconnect epoch
       (5 attempts, exponential backoff with jitter) defined in
       ``docs/ADAPTER_PLUGIN_INTERFACE.md`` §Reconnect contract.
    5. Shut down cleanly on SIGTERM / SIGINT, draining each channel.

The gateway intentionally never imports a channel concrete — it discovers
adapters via ``ChannelRegistry``, which is populated by the side-effect
import of ``pf_runtime.channels`` performed inside ``run_gateway``.
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import random
import signal
from pathlib import Path
from typing import Any

from pf_runtime.channels.adapter_base import (
    Channel,
    ChannelError,
    ChannelRegistry,
)
from pf_runtime.channels.slack import atlas_decision_card_blocks
from pf_runtime.config import OutboundMessage, Profile, load_profile
from pf_runtime.dream.post_session import DreamLoop, PostSessionJob
from pf_runtime.memory import MemoryStack
from pf_runtime.memory.tier1_soul import SoulReader
from pf_runtime.memory.tier2_buffer import BufferStore
from pf_runtime.memory.tier3_episodic import episodic_client_from_env
from pf_runtime.memory.tier4_skills import default_skill_registry
from pf_runtime.runtime.builtin_tools import builtin_tools_for_profile
from pf_runtime.runtime.inbound_ledger import SqliteInboundLedger
from pf_runtime.runtime.loop import run_session
from pf_runtime.runtime.model_adapter import ModelAdapter, RoutingModelAdapter
from pf_runtime.runtime.pfos_emit import (
    emit_agent_event,
    runtime_reply_payload,
)
from pf_runtime.runtime.pfos_emit import (
    is_configured as pfos_emit_configured,
)
from pf_runtime.runtime.sentry_init import init_sentry_from_profile

_log = logging.getLogger(__name__)


def _pfos_reply_emit_wanted() -> bool:
    """True when PFOS URL+token are set and ``PFOS_EMIT_MODE`` allows reply emits.

    ``PFOS_EMIT_MODE`` (default ``reply``): ``off`` / ``false`` / ``0`` / ``no``
    disables; ``reply`` / ``reply_only`` / ``full`` enable (``full`` reserved for
    additional milestones).
    """
    if not pfos_emit_configured():
        return False
    mode = os.environ.get("PFOS_EMIT_MODE", "reply").strip().lower()
    if mode in ("off", "false", "0", "no", "disabled"):
        return False
    if mode in ("reply", "reply_only", "full", ""):
        return True
    _log.warning("unknown PFOS_EMIT_MODE=%r; emitting reply events", mode)
    return True


# Per-epoch reconnect budget (see ADAPTER_PLUGIN_INTERFACE.md §Reconnect).
_MAX_EPOCH_ATTEMPTS = 5
_BASE_BACKOFF_SECONDS = 1.0
_MAX_BACKOFF_SECONDS = 60.0


async def run_gateway(
    profile_slug: str,
    hermes_home: Path,
    *,
    channel_names: list[str] | None = None,
) -> None:
    """Run the long-running channel gateway for ``profile_slug``.

    Blocks until SIGTERM / SIGINT (or until every channel exhausts its
    reconnect budget).

    Args:
        profile_slug: Profile identifier (e.g. ``"personal"``).
        hermes_home: Path to the Hermes home dir (typically ``~/.hermes``).
        channel_names: Channel adapter names to enable. Defaults to
            ``["slack"]``.
    """
    # Side-effect import — populates the ChannelRegistry. Done here (not at
    # module top) so this gateway module remains channel-agnostic per ADR.
    import pf_runtime.channels  # noqa: F401

    if channel_names is None:
        channel_names = ["slack"]

    profile = load_profile(profile_slug, hermes_home=hermes_home)
    init_sentry_from_profile(profile, component="gateway")
    adapter: ModelAdapter = RoutingModelAdapter(
        env_path=profile.env_path,
        fallback_model=profile.model,
    )

    # Build the memory stack ONCE for the lifetime of the gateway. Mirrors
    # __main__._run() but uses the manual open()/close() lifecycle since
    # the gateway lives indefinitely (no `with` block).
    soul_reader = SoulReader()
    buffer = BufferStore(profile.slug)
    buffer.open()
    memory = MemoryStack(
        soul=soul_reader,
        buffer=buffer,
        episodic=episodic_client_from_env(),
        skills=default_skill_registry(hermes_home),
    )
    tools = builtin_tools_for_profile(profile)

    dream_loop = DreamLoop(hermes_home)
    dream_loop.start()

    # Build & connect channels.
    channels: list[Channel] = []
    consumer_tasks: list[asyncio.Task[None]] = []
    try:
        for name in channel_names:
            cls: Any = ChannelRegistry.get(name)
            if name == "slack":
                ledger_path = (
                    profile.env_path.parent / "runtime-state" / "inbound_dedup.sqlite"
                )
                ledger = SqliteInboundLedger(ledger_path)
                ch = cls(
                    profile_slug=profile.slug,
                    env_path=profile.env_path,
                    inbound_ledger=ledger,
                )
            else:
                ch = cls(profile_slug=profile.slug, env_path=profile.env_path)
            await ch.connect()
            channels.append(ch)

        consumer_tasks = [
            asyncio.create_task(
                _consume_inbound(ch, profile, adapter, memory, dream_loop, tools),
            )
            for ch in channels
        ]

        # Block on SIGTERM / SIGINT.
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                # add_signal_handler is unsupported on some platforms (e.g.
                # Windows); the gateway is Unix-only in throwaway, so this
                # path is informational only.
                _log.warning("Signal handler for %s not supported on this platform", sig)

        await stop.wait()

    finally:
        for t in consumer_tasks:
            t.cancel()
        if consumer_tasks:
            await asyncio.gather(*consumer_tasks, return_exceptions=True)
        for ch in channels:
            try:
                await ch.disconnect()
            except Exception as e:
                _log.warning("disconnect error %s: %s", ch.name, e)
        with contextlib.suppress(Exception):
            buffer.close()
        with contextlib.suppress(Exception):
            await dream_loop.stop()


# Fire-and-forget PFOS emits — keep strong refs until each task completes.
_background_pfos_tasks: set[asyncio.Task[None]] = set()


def _schedule_pfos_reply_event(
    *,
    channel_name: str,
    profile_slug: str,
    assistant_reply: str,
    session_id: str,
    inbound_preview: str,
) -> None:
    task = asyncio.create_task(
        _safe_pfos_reply_event(
            channel_name=channel_name,
            profile_slug=profile_slug,
            assistant_reply=assistant_reply,
            session_id=session_id,
            inbound_preview=inbound_preview,
        ),
    )
    _background_pfos_tasks.add(task)
    task.add_done_callback(_background_pfos_tasks.discard)


async def _safe_pfos_reply_event(
    *,
    channel_name: str,
    profile_slug: str,
    assistant_reply: str,
    session_id: str,
    inbound_preview: str,
) -> None:
    """Fire-and-forget PFOS writeback; failures must not affect channel I/O."""
    try:
        payload = runtime_reply_payload(
            channel=channel_name,
            profile_slug=profile_slug,
            text_preview=assistant_reply,
            session_id=session_id,
            inbound_preview=inbound_preview,
        )
        await emit_agent_event(payload)
    except Exception:
        _log.exception("pfos agent-event emit failed (non-fatal)")


async def _consume_inbound(
    channel: Channel,
    profile: Profile,
    adapter: ModelAdapter,
    memory: MemoryStack,
    dream_loop: DreamLoop,
    tools: list[Any] | None = None,
) -> None:
    """Per-channel consumer loop with reconnect-epoch resilience.

    On a successful receive cycle, the epoch counter is reset. On a
    ``ChannelError`` the consumer enters a reconnect epoch: up to
    ``_MAX_EPOCH_ATTEMPTS`` attempts with exponential-jittered backoff. A
    successful reconnect within the epoch resets the counter; exhaustion
    disables the channel (disconnect + return).

    A single bad message MUST NOT kill the consumer — handler exceptions
    are logged and the next message is processed.
    """
    epoch_attempts = 0

    while True:
        try:
            async for inbound in channel.receive():
                try:
                    await _handle_inbound(
                        channel, inbound, profile, adapter, memory, dream_loop, tools,
                    )
                except Exception:
                    _log.exception(
                        "handler error on %s/%s",
                        channel.name,
                        inbound.message_id,
                    )

        except asyncio.CancelledError:
            raise
        except ChannelError as e:
            epoch_attempts += 1
            if epoch_attempts > _MAX_EPOCH_ATTEMPTS:
                _log.error(
                    "channel %s exhausted reconnect budget (%d attempts); disabling",
                    channel.name,
                    _MAX_EPOCH_ATTEMPTS,
                )
                with contextlib.suppress(Exception):
                    await channel.disconnect()
                return

            # Exponential backoff with full jitter (factor 0.5-1.5x).
            base_delay = min(
                _MAX_BACKOFF_SECONDS,
                _BASE_BACKOFF_SECONDS * (2 ** (epoch_attempts - 1)),
            )
            delay = base_delay * (0.5 + random.random())  # nosec B311
            _log.warning(
                "channel %s error (%s); reconnect attempt %d/%d in %.2fs",
                channel.name,
                e,
                epoch_attempts,
                _MAX_EPOCH_ATTEMPTS,
                delay,
            )
            await asyncio.sleep(delay)
            try:
                await channel.connect()
                # Successful reconnect — close the epoch.
                epoch_attempts = 0
            except ChannelError:
                # Stay inside the epoch; the next loop iteration retries.
                continue


async def _handle_inbound(
    channel: Channel,
    inbound: object,
    profile: Profile,
    adapter: ModelAdapter,
    memory: MemoryStack,
    dream_loop: DreamLoop,
    tools: list[Any] | None = None,
) -> None:
    """Drive a single inbound through ``run_session`` and reply via channel."""
    # ``inbound`` is an InboundMessage; typed loosely here so test stubs can
    # pass minimal mock objects.
    from pf_runtime.config import InboundMessage  # local — avoid cycle

    if not isinstance(inbound, InboundMessage):
        raise TypeError(
            f"_handle_inbound expected InboundMessage, got {type(inbound).__name__}",
        )

    result = await run_session(
        profile,
        inbound,
        model_adapter=adapter,
        memory=memory,
        tools=tools,
    )

    assistant_reply = ""
    for m in reversed(result.messages):
        if m.role == "assistant":
            assistant_reply = m.content
            break
    if not assistant_reply:
        return

    outbound_metadata = {"thread_ts": inbound.metadata.get("thread_ts", "")}
    if channel.name == "slack":
        card = result.metadata.get("atlas_slack_decision_card")
        if isinstance(card, dict):
            base_url = ""
            if profile.env_path.exists():
                env_text = profile.env_path.read_text(encoding="utf-8")
                for raw in env_text.splitlines():
                    if raw.strip().startswith("PFOS_BASE_URL="):
                        base_url = raw.partition("=")[2].strip().strip('"').strip("'")
                        break
            outbound_metadata["blocks"] = atlas_decision_card_blocks(
                card,
                base_url=base_url,
            )

    outbound = OutboundMessage(
        channel=channel.name,
        profile_slug=profile.slug,
        # Reply into the DM channel surfaced by the inbound metadata; fall
        # back to the user id (Slack lets us postMessage by U… and we'll
        # resolve to a D… via conversations.open).
        target_user_id=inbound.metadata.get("channel_id", inbound.user_id),
        text=assistant_reply,
        metadata=outbound_metadata,
        in_reply_to=inbound.message_id,
        message_id=f"{channel.name}-reply-{inbound.message_id}",
    )
    await channel.send(outbound)
    if _pfos_reply_emit_wanted():
        _schedule_pfos_reply_event(
            channel_name=channel.name,
            profile_slug=profile.slug,
            assistant_reply=assistant_reply,
            session_id=result.session_id,
            inbound_preview=inbound.text,
        )
    await channel.ack(inbound.message_id)

    await dream_loop.schedule(
        PostSessionJob(
            profile_slug=profile.slug,
            session_id=result.session_id,
            channel=channel.name,
            user_preview=inbound.text,
            assistant_preview=assistant_reply,
        ),
    )
