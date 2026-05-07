"""Gateway consumer reconnect-epoch tests.

Drives ``_consume_inbound`` directly with a fake channel + monkeypatched
``run_session`` so the test never reaches OpenRouter or Slack.
"""
from __future__ import annotations

import asyncio
import contextlib
from collections import deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import pytest

from pf_runtime.channels.adapter_base import (
    Channel,
    ChannelConnectError,
    ChannelError,
)
from pf_runtime.config import InboundMessage, Message, OutboundMessage

# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #


@dataclass
class _FakeProfile:
    slug: str = "test"


class _ReconnectChannel(Channel):
    """Channel that fails N times after each receive batch, then recovers."""

    name = "reconnect-fake"

    def __init__(
        self,
        *,
        batches: list[list[InboundMessage]],
        connect_failures: int = 0,
    ) -> None:
        self.name = "reconnect-fake"
        self.profile_slug = "test"
        self._batches: deque[list[InboundMessage]] = deque(batches)
        self._connect_failures_remaining = connect_failures
        self.connect_calls = 0
        self.disconnect_calls = 0
        self.sent: list[OutboundMessage] = []
        self.acked: list[str] = []
        self._current_batch: list[InboundMessage] = []

    async def connect(self) -> None:
        self.connect_calls += 1
        if self._connect_failures_remaining > 0:
            self._connect_failures_remaining -= 1
            raise ChannelConnectError("simulated connect failure")
        self._connected = True

    async def receive(self) -> AsyncIterator[InboundMessage]:
        if not self._batches:
            # Block forever if nothing left — caller cancels us.
            await asyncio.Event().wait()
            return
        self._current_batch = self._batches.popleft()
        for m in self._current_batch:
            yield m
        # After yielding the batch, simulate a transport fault — but only
        # if more batches remain; the final batch ends naturally so the
        # generator exits and the consumer can be cancelled.
        if self._batches:
            raise ChannelError("simulated batch-end transport fault")

    async def send(self, msg: OutboundMessage) -> None:
        self.sent.append(msg)

    async def typing(self, target_user_id: str, on: bool) -> None:
        return

    async def ack(self, message_id: str) -> None:
        self.acked.append(message_id)

    async def disconnect(self) -> None:
        self.disconnect_calls += 1
        self._connected = False


@dataclass
class _FakeSessionResult:
    messages: list[Message]
    steps: int = 1
    finish_reason: str = "stop"
    cost_usd: Decimal = Decimal("0")


async def _fake_run_session(profile: Any, inbound: Any, **_: Any) -> _FakeSessionResult:
    return _FakeSessionResult(
        messages=[
            Message(role="user", content=inbound.text),
            Message(role="assistant", content=f"echo: {inbound.text}"),
        ],
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_consumer_survives_three_transient_errors_with_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """3 ChannelError + reconnect cycles → all messages eventually delivered."""
    from pf_runtime.runtime import gateway

    # Speed up the test — collapse jittered backoff to ~zero.
    monkeypatch.setattr(gateway, "_BASE_BACKOFF_SECONDS", 0.001)
    monkeypatch.setattr(gateway, "_MAX_BACKOFF_SECONDS", 0.005)
    monkeypatch.setattr(gateway, "run_session", _fake_run_session)

    batches = [
        [
            InboundMessage(
                channel="reconnect-fake",
                profile_slug="test",
                user_id="U1",
                text=f"b{batch_i}-m{i}",
                message_id=f"b{batch_i}-m{i}",
                metadata={"channel_id": "D1", "ts": "1.0", "thread_ts": "1.0"},
            )
            for i in range(2)
        ]
        for batch_i in range(4)  # 4 batches → 3 transport faults between them
    ]
    ch = _ReconnectChannel(batches=batches)
    profile = _FakeProfile()

    task = asyncio.create_task(
        gateway._consume_inbound(ch, profile, adapter=None, memory=None)  # type: ignore[arg-type]
    )

    # Give the consumer time to drain all 4 batches across 3 reconnects.
    # Final batch leaves the receive() generator blocked on Event().wait().
    deadline = asyncio.get_event_loop().time() + 2.0
    while asyncio.get_event_loop().time() < deadline:
        if len(ch.sent) >= 8:
            break
        await asyncio.sleep(0.01)

    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task

    assert len(ch.sent) == 8, f"expected 8 sends, got {len(ch.sent)}"
    # connect_calls = 1 initial (in run_gateway, which we bypass) + 3 reconnects.
    # Here we drive _consume_inbound directly, so initial connect is not
    # part of the call — it should be exactly 3 reconnect attempts.
    assert ch.connect_calls == 3, (
        f"expected 3 reconnect calls, got {ch.connect_calls}"
    )


class _AlwaysFailsChannel(Channel):
    """Channel whose receive() raises ChannelError immediately and whose
    connect() always fails — used to drive the reconnect-budget exhaustion
    path without any message-delivery interference.
    """

    name = "always-fails"

    def __init__(self) -> None:
        self.name = "always-fails"
        self.profile_slug = "test"
        self.connect_calls = 0
        self.disconnect_calls = 0

    async def connect(self) -> None:
        self.connect_calls += 1
        raise ChannelConnectError("connect always fails")

    async def receive(self) -> AsyncIterator[InboundMessage]:
        # An async generator that raises before yielding — drives the
        # consumer straight into the reconnect epoch on every iteration.
        if self.connect_calls >= 0:
            raise ChannelError("receive always fails")
        yield InboundMessage(
            channel="always-fails",
            profile_slug="test",
            user_id="U1",
            text="unreachable",
            message_id="unreachable",
        )

    async def send(self, msg: OutboundMessage) -> None:
        return

    async def typing(self, target_user_id: str, on: bool) -> None:
        return

    async def ack(self, message_id: str) -> None:
        return

    async def disconnect(self) -> None:
        self.disconnect_calls += 1


@pytest.mark.asyncio
async def test_consumer_exits_after_budget_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """6 consecutive ChannelError epochs → consumer exits + channel disconnects.

    With ``_MAX_EPOCH_ATTEMPTS=5`` the consumer survives 5 failures and exits
    on the 6th. Connect is attempted 5 times (one per epoch attempt) before
    the 6th ChannelError trips the budget guard.
    """
    from pf_runtime.runtime import gateway

    monkeypatch.setattr(gateway, "_BASE_BACKOFF_SECONDS", 0.001)
    monkeypatch.setattr(gateway, "_MAX_BACKOFF_SECONDS", 0.005)
    monkeypatch.setattr(gateway, "run_session", _fake_run_session)

    ch = _AlwaysFailsChannel()
    profile = _FakeProfile()

    # _consume_inbound returns cleanly when the budget is blown — no exception.
    await asyncio.wait_for(
        gateway._consume_inbound(ch, profile, adapter=None, memory=None),  # type: ignore[arg-type]
        timeout=2.0,
    )

    assert ch.disconnect_calls >= 1
    # Receive raises 6 times (epoch_attempts increments 1..6); on the 6th
    # the guard exits BEFORE attempting another connect — so we observe
    # exactly 5 connect calls.
    assert ch.connect_calls == 5, (
        f"expected 5 reconnect attempts, got {ch.connect_calls}"
    )
