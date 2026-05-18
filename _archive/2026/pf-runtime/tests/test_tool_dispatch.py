"""ToolDispatcher validation, cycle detection, and loop integration."""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

import pytest

from pf_runtime.communications.tools import CreateProposalTool
from pf_runtime.config import InboundMessage, Profile
from pf_runtime.runtime.loop import run_session
from pf_runtime.runtime.model_adapter import ModelAdapter
from pf_runtime.runtime.tool_dispatch import (
    Tool,
    ToolContext,
    ToolCycleError,
    ToolDispatcher,
    ToolResult,
    ToolValidationError,
)


class _EchoTool(Tool):
    name = "test.echo"
    description = "Echo a string."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "required": ["text"],
        "properties": {"text": {"type": "string", "minLength": 1}},
        "additionalProperties": False,
    }

    def __init__(self) -> None:
        self.calls = 0

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        self.calls += 1
        return ToolResult(ok=True, output={"text": args["text"]}, cost_usd=Decimal("0"))


class _SequenceAdapter(ModelAdapter):
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.messages: list[list[dict[str, Any]]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del model, max_tokens
        self.messages.append(messages)
        return self.replies.pop(0), Decimal("0.01")


def test_dispatcher_rejects_invalid_args() -> None:
    dispatcher = ToolDispatcher([_EchoTool()])
    with pytest.raises(ToolValidationError):
        import asyncio

        asyncio.run(
            dispatcher.dispatch(
                "test.echo",
                {"text": "", "extra": True},
                ToolContext(profile_slug="p", session_id="s"),
            )
        )


@pytest.mark.asyncio
async def test_dispatcher_detects_repeated_tool_cycle() -> None:
    dispatcher = ToolDispatcher([_EchoTool()], max_same_call=1)
    ctx = ToolContext(profile_slug="p", session_id="s")
    await dispatcher.dispatch("test.echo", {"text": "hi"}, ctx)
    with pytest.raises(ToolCycleError):
        await dispatcher.dispatch("test.echo", {"text": "hi"}, ctx)


@pytest.mark.asyncio
async def test_run_session_dispatches_tool_and_finishes(tmp_path: Path) -> None:
    profile = _profile(tmp_path)
    adapter = _SequenceAdapter(
        [
            json.dumps(
                {
                    "tool_call": {
                        "name": "communications.propose_action",
                        "arguments": {
                            "action_id": "p1",
                            "action_type": "reply_draft",
                            "account_id": "gmail-1",
                            "target_id": "m1",
                            "rationale": "needs Alex today",
                            "payload": {"draft": "Thanks, I will review."},
                        },
                    }
                }
            ),
            "I created one proposed reply for Alex review.",
        ]
    )
    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="personal",
            user_id="alex",
            text="triage",
        ),
        model_adapter=adapter,
        tools=[CreateProposalTool(tmp_path / "communications.sqlite")],
    )
    assert result.steps == 2
    assert result.finish_reason == "stop"
    assert "proposed reply" in result.messages[-1].content
    assert any(m["role"] == "tool" for m in adapter.messages[-1])


@pytest.mark.asyncio
async def test_run_session_dispatches_leading_tool_json_with_trailing_text(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path)
    tool = _EchoTool()
    adapter = _SequenceAdapter(
        [
            json.dumps(
                {
                    "tool_call": {
                        "name": "test.echo",
                        "arguments": {"text": "receipt-first"},
                    }
                }
            )
            + " fake receipt text",
            "Tool result received.",
        ]
    )

    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="personal", user_id="alex", text="echo"),
        model_adapter=adapter,
        tools=[tool],
    )

    assert result.steps == 2
    assert tool.calls == 1
    assert result.messages[-1].content == "Tool result received."
    assert any(m["role"] == "tool" for m in adapter.messages[-1])


@pytest.mark.asyncio
async def test_run_session_dispatches_prefixed_loose_tool_json(tmp_path: Path) -> None:
    profile = _profile(tmp_path)
    tool = _EchoTool()
    adapter = _SequenceAdapter(
        [
            '[DEGRADED_MODEL_ROUTE]\n{"name":"test.echo","arguments":{"text":"loose"}}',
            "Tool result received.",
        ]
    )

    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="personal", user_id="alex", text="echo"),
        model_adapter=adapter,
        tools=[tool],
    )

    assert result.steps == 2
    assert tool.calls == 1
    assert result.messages[-1].content == "Tool result received."


@pytest.mark.asyncio
async def test_run_session_enforces_cost_ceiling(tmp_path: Path) -> None:
    profile = _profile(tmp_path)
    adapter = _SequenceAdapter(["This answer is long enough."])
    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="personal", user_id="alex", text="hi"),
        model_adapter=adapter,
        cost_ceiling_usd=Decimal("0.001"),
    )
    assert result.finish_reason == "cost_ceiling"


def _profile(tmp_path: Path) -> Profile:
    for name in ("SOUL.md", "USER.md", "MEMORY.md", ".env"):
        (tmp_path / name).write_text("# x\n", encoding="utf-8")
    return Profile(
        slug="personal",
        model="x/y",
        provider="openrouter",
        soul_md_path=tmp_path / "SOUL.md",
        user_md_path=tmp_path / "USER.md",
        memory_md_path=tmp_path / "MEMORY.md",
        env_path=tmp_path / ".env",
    )
