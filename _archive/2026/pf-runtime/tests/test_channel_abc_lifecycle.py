"""Channel ABC lifecycle + dedup + chaos tests against an in-test FakeChannel."""
from __future__ import annotations

from collections import deque
from collections.abc import AsyncIterator

import pytest

from pf_runtime.channels.adapter_base import (
    Channel,
    ChannelConnectError,
    ChannelError,
)
from pf_runtime.config import InboundMessage, OutboundMessage


class FakeChannel(Channel):
    """In-memory ``Channel`` impl with chaos hooks for testing."""

    name = "fake"

    def __init__(
        self,
        profile_slug: str = "test",
        *,
        fail_after_n_receives: int | None = None,
        fail_count: int = 0,
        force_connect_failure: bool = False,
    ) -> None:
        self.name = "fake"
        self.profile_slug = profile_slug
        self._inbox: deque[InboundMessage] = deque()
        self.sent: list[OutboundMessage] = []
        self._outbound_dedup: set[str] = set()
        self._receive_count = 0
        self._fail_after_n_receives = fail_after_n_receives
        self._fail_count = fail_count
        self._force_connect_failure = force_connect_failure
        self.connect_calls = 0
        self.acks: list[str] = []

    def preload(self, messages: list[InboundMessage]) -> None:
        self._inbox.extend(messages)

    async def connect(self) -> None:
        self.connect_calls += 1
        if self._force_connect_failure:
            raise ChannelConnectError("forced connect failure")
        self._connected = True

    async def receive(self) -> AsyncIterator[InboundMessage]:
        while self._inbox:
            self._receive_count += 1
            if (
                self._fail_after_n_receives is not None
                and self._fail_count > 0
                and self._receive_count > self._fail_after_n_receives
            ):
                self._fail_count -= 1
                self._receive_count = 0
                raise ChannelError("simulated transient receive failure")
            yield self._inbox.popleft()

    async def send(self, msg: OutboundMessage) -> None:
        if msg.message_id in self._outbound_dedup:
            return
        self._outbound_dedup.add(msg.message_id)
        self.sent.append(msg)

    async def typing(self, target_user_id: str, on: bool) -> None:
        return

    async def ack(self, message_id: str) -> None:
        self.acks.append(message_id)

    async def disconnect(self) -> None:
        self._connected = False


@pytest.mark.asyncio
async def test_lifecycle_connect_send_ack_disconnect() -> None:
    ch = FakeChannel()
    await ch.connect()
    assert ch._connected is True
    out = OutboundMessage(
        channel="fake",
        profile_slug="test",
        target_user_id="U1",
        text="hi",
        message_id="m1",
    )
    await ch.send(out)
    await ch.ack("inbound-1")
    await ch.disconnect()
    assert (await ch.health()).ok is False
    assert len(ch.sent) == 1
    assert ch.acks == ["inbound-1"]


@pytest.mark.asyncio
async def test_outbound_dedup_on_message_id() -> None:
    ch = FakeChannel()
    await ch.connect()
    out = OutboundMessage(
        channel="fake",
        profile_slug="test",
        target_user_id="U1",
        text="hi",
        message_id="dup",
    )
    await ch.send(out)
    await ch.send(out)
    assert len(ch.sent) == 1


@pytest.mark.asyncio
async def test_chaos_zero_loss_zero_dup_across_drops() -> None:
    """Preload 50 messages, fail-and-recover 3 times during consumption.

    Drives receive() + connect() directly without dragging the gateway in.
    Asserts every original message is delivered exactly once.
    """
    preload = [
        InboundMessage(
            channel="fake",
            profile_slug="test",
            user_id="U1",
            text=f"msg-{i}",
            message_id=f"m-{i}",
        )
        for i in range(50)
    ]
    ch = FakeChannel(fail_after_n_receives=10, fail_count=3)
    ch.preload(preload)
    await ch.connect()

    received: list[InboundMessage] = []
    drops = 0
    max_attempts = 10
    while True:
        max_attempts -= 1
        if max_attempts < 0:
            raise AssertionError("fake channel did not drain within reconnect budget")
        try:
            async for msg in ch.receive():
                received.append(msg)
            # Generator exited cleanly because the inbox is empty.
            break
        except ChannelError:
            drops += 1
            await ch.connect()

    assert drops == 3, f"expected 3 simulated drops, got {drops}"
    assert len(received) == 50
    ids = [m.message_id for m in received]
    assert ids == [f"m-{i}" for i in range(50)]  # zero loss + zero duplication
