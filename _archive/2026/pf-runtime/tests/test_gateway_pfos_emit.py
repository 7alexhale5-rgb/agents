"""Gateway schedules PFOS emit after outbound send when env is set."""
from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pf_runtime.config import InboundMessage, Message
from pf_runtime.runtime.gateway import _handle_inbound
from pf_runtime.runtime.loop import SessionResult


@pytest.mark.asyncio
async def test_handle_inbound_schedules_pfos_emit_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PFOS_AGENT_EVENT_URL",
        "https://os.example/api/silos/fleet/agent-event",
    )
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")
    monkeypatch.delenv("PFOS_EMIT_MODE", raising=False)

    emit_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("pf_runtime.runtime.gateway.emit_agent_event", emit_mock)

    channel = MagicMock()
    channel.name = "slack"
    channel.send = AsyncMock()
    channel.ack = AsyncMock()

    profile = MagicMock()
    profile.slug = "personal"

    dream_loop = MagicMock()
    dream_loop.schedule = AsyncMock()

    inbound = InboundMessage(
        channel="slack",
        profile_slug="personal",
        user_id="U1",
        text="hello",
        metadata={"channel_id": "C1"},
        message_id="m1",
    )

    session_result = SessionResult(
        messages=[
            Message(role="user", content="hello"),
            Message(role="assistant", content="hi there"),
        ],
        steps=1,
        finish_reason="stop",
        cost_usd=Decimal("0"),
        session_id="sess-99",
    )

    with patch(
        "pf_runtime.runtime.gateway.run_session",
        new=AsyncMock(return_value=session_result),
    ):
        await _handle_inbound(
            channel,
            inbound,
            profile,
            MagicMock(),
            MagicMock(),
            dream_loop,
        )

    channel.send.assert_awaited_once()
    channel.ack.assert_awaited_once()
    dream_loop.schedule.assert_awaited_once()

    await asyncio.sleep(0)
    emit_mock.assert_awaited_once()
    call_kw = emit_mock.call_args[0][0]
    assert call_kw["type"] == "STATE_CHANGED"
    assert call_kw["trace_id"] == "sess-99"
    assert call_kw["data"]["kind"] == "pf_runtime_reply"
    assert call_kw["data"]["session_id"] == "sess-99"


@pytest.mark.asyncio
async def test_handle_inbound_skips_pfos_emit_when_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PFOS_AGENT_EVENT_URL", raising=False)
    monkeypatch.delenv("PFOS_AGENT_EVENT_TOKEN", raising=False)

    emit_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("pf_runtime.runtime.gateway.emit_agent_event", emit_mock)

    channel = MagicMock()
    channel.name = "slack"
    channel.send = AsyncMock()
    channel.ack = AsyncMock()

    profile = MagicMock()
    profile.slug = "personal"

    dream_loop = MagicMock()
    dream_loop.schedule = AsyncMock()

    session_result = SessionResult(
        messages=[
            Message(role="user", content="hello"),
            Message(role="assistant", content="reply"),
        ],
        steps=1,
        finish_reason="stop",
        cost_usd=Decimal("0"),
        session_id="s1",
    )

    with patch(
        "pf_runtime.runtime.gateway.run_session",
        new=AsyncMock(return_value=session_result),
    ):
        await _handle_inbound(
            channel,
            InboundMessage(
                channel="slack",
                profile_slug="personal",
                user_id="U1",
                text="hello",
                message_id="m1",
            ),
            profile,
            MagicMock(),
            MagicMock(),
            dream_loop,
        )

    await asyncio.sleep(0)
    emit_mock.assert_not_called()


@pytest.mark.asyncio
async def test_handle_inbound_skips_pfos_when_emit_mode_off(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PFOS_AGENT_EVENT_URL",
        "https://os.example/api/silos/fleet/agent-event",
    )
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")
    monkeypatch.setenv("PFOS_EMIT_MODE", "off")

    emit_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("pf_runtime.runtime.gateway.emit_agent_event", emit_mock)

    channel = MagicMock()
    channel.name = "slack"
    channel.send = AsyncMock()
    channel.ack = AsyncMock()

    profile = MagicMock()
    profile.slug = "personal"

    dream_loop = MagicMock()
    dream_loop.schedule = AsyncMock()

    session_result = SessionResult(
        messages=[
            Message(role="user", content="hello"),
            Message(role="assistant", content="reply"),
        ],
        steps=1,
        finish_reason="stop",
        cost_usd=Decimal("0"),
        session_id="s1",
    )

    with patch(
        "pf_runtime.runtime.gateway.run_session",
        new=AsyncMock(return_value=session_result),
    ):
        await _handle_inbound(
            channel,
            InboundMessage(
                channel="slack",
                profile_slug="personal",
                user_id="U1",
                text="hello",
                message_id="m1",
            ),
            profile,
            MagicMock(),
            MagicMock(),
            dream_loop,
        )

    await asyncio.sleep(0)
    emit_mock.assert_not_called()
