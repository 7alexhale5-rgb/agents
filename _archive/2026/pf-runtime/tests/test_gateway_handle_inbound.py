"""_handle_inbound: outbound idempotency id, dream enqueue, type guard."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pf_runtime.config import InboundMessage, Message, OutboundMessage, Profile
from pf_runtime.dream.post_session import DreamLoop
from pf_runtime.memory import MemoryStack
from pf_runtime.runtime import gateway as gateway_mod
from pf_runtime.runtime.gateway import _handle_inbound
from pf_runtime.runtime.loop import SessionResult
from pf_runtime.runtime.model_adapter import ModelAdapter


@dataclass
class _RecChannel:
    name: str = "slack"

    def __init__(self) -> None:
        self.sent: list[OutboundMessage] = []
        self.acked: list[str] = []

    async def send(self, msg: OutboundMessage) -> None:
        self.sent.append(msg)

    async def ack(self, message_id: str) -> None:
        self.acked.append(message_id)


@pytest.mark.asyncio
async def test_handle_inbound_builds_deterministic_outbound_and_enqueues_dream(
    tmp_path: Any,
) -> None:
    ch = _RecChannel()
    profile = Profile(
        slug="personal",
        model="x/y",
        provider="openrouter",
        soul_md_path=tmp_path / "S",
        user_md_path=tmp_path / "U",
        memory_md_path=tmp_path / "M",
        env_path=tmp_path / ".env",
    )
    for p in (profile.soul_md_path, profile.user_md_path, profile.memory_md_path):
        p.write_text("# x", encoding="utf-8")
    profile.env_path.write_text("K=v\n", encoding="utf-8")

    inbound = InboundMessage(
        channel="slack",
        profile_slug="personal",
        user_id="U1",
        text="hi",
        message_id="evt-99",
        metadata={"channel_id": "D111", "thread_ts": "1.0"},
    )

    adapter = MagicMock(spec=ModelAdapter)
    memory = MagicMock(spec=MemoryStack)
    dream = DreamLoop(tmp_path / "hermes")
    dream.start()

    captured: dict[str, Any] = {}

    async def fake_run_session(*args: Any, **kwargs: Any) -> Any:
        captured["called"] = True
        return SessionResult(
            messages=[
                Message(role="user", content="hi"),
                Message(role="assistant", content="hello back"),
            ],
            steps=1,
            finish_reason="stop",
            cost_usd=Decimal("0"),
            session_id="sess-xyz",
        )

    with patch.object(gateway_mod, "run_session", fake_run_session):
        await _handle_inbound(ch, inbound, profile, adapter, memory, dream)

    assert captured.get("called") is True
    assert len(ch.sent) == 1
    assert ch.sent[0].message_id == "slack-reply-evt-99"
    assert ch.sent[0].in_reply_to == "evt-99"
    assert ch.acked == ["evt-99"]

    await dream._queue.join()
    audit = (
        tmp_path
        / "hermes"
        / "profiles"
        / "personal"
        / "runtime-state"
        / "post_session_audit.jsonl"
    )
    text = audit.read_text(encoding="utf-8")
    assert "sess-xyz" in text
    assert "hello back" in text

    await dream.stop()


@pytest.mark.asyncio
async def test_handle_inbound_wrong_type_raises() -> None:
    ch = _RecChannel()
    profile = MagicMock(spec=Profile)
    profile.slug = "p"
    adapter = MagicMock(spec=ModelAdapter)
    memory = MagicMock(spec=MemoryStack)
    dream = MagicMock(spec=DreamLoop)
    dream.schedule = AsyncMock()

    with pytest.raises(TypeError, match="InboundMessage"):
        await _handle_inbound(ch, "not-a-message", profile, adapter, memory, dream)


@pytest.mark.asyncio
async def test_handle_inbound_no_assistant_skips_send(
    tmp_path: Any,
) -> None:
    ch = _RecChannel()
    profile = Profile(
        slug="personal",
        model="x/y",
        provider="openrouter",
        soul_md_path=tmp_path / "Sv",
        user_md_path=tmp_path / "Uv",
        memory_md_path=tmp_path / "Mv",
        env_path=tmp_path / ".env",
    )
    for p in (profile.soul_md_path, profile.user_md_path, profile.memory_md_path):
        p.write_text("# x", encoding="utf-8")
    profile.env_path.write_text("K=v\n", encoding="utf-8")

    inbound = InboundMessage(
        channel="slack",
        profile_slug="personal",
        user_id="U1",
        text="hi",
        message_id="evt-1",
        metadata={"channel_id": "D1"},
    )

    async def only_user(*_a: Any, **_k: Any) -> Any:
        return SessionResult(
            messages=[Message(role="user", content="hi")],
            steps=1,
            finish_reason="stop",
            cost_usd=Decimal("0"),
            session_id="s1",
        )

    dream = DreamLoop(tmp_path / "h")
    dream.start()
    with patch.object(gateway_mod, "run_session", only_user):
        await _handle_inbound(
            ch,
            inbound,
            profile,
            MagicMock(spec=ModelAdapter),
            MagicMock(spec=MemoryStack),
            dream,
        )
    assert ch.sent == []
    assert ch.acked == []
    await dream.stop()
