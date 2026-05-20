"""ChannelRegistry lookup + error tests."""
from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from pf_runtime.channels.adapter_base import Channel, ChannelRegistry
from pf_runtime.config import InboundMessage, OutboundMessage


class _StubChannel(Channel):
    """Minimal Channel impl used to exercise the registry."""

    name = "stub-for-registry-test"

    def __init__(self, profile_slug: str = "test") -> None:
        self.name = "stub-for-registry-test"
        self.profile_slug = profile_slug

    async def connect(self) -> None:
        self._connected = True

    async def receive(self) -> AsyncIterator[InboundMessage]:
        messages: list[InboundMessage] = []
        for msg in messages:
            yield msg

    async def send(self, msg: OutboundMessage) -> None:
        return

    async def typing(self, target_user_id: str, on: bool) -> None:
        return

    async def ack(self, message_id: str) -> None:
        return

    async def disconnect(self) -> None:
        self._connected = False


def test_register_and_get_returns_class() -> None:
    name = "stub-registry-roundtrip"
    ChannelRegistry.register(name, _StubChannel)
    assert ChannelRegistry.get(name) is _StubChannel


def test_get_unknown_raises_key_error_with_registered_list() -> None:
    with pytest.raises(KeyError) as excinfo:
        ChannelRegistry.get("nonexistent-xyz")
    # The message should include "Registered channels" so callers can
    # diagnose typos.
    assert "Registered channels" in str(excinfo.value)
