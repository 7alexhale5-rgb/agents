from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

import pytest

from pf_runtime.config import InboundMessage, Profile
from pf_runtime.runtime.loop import run_session
from pf_runtime.runtime.model_adapter import ModelAdapter
from pf_runtime.runtime.tool_dispatch import Tool, ToolContext, ToolResult


class _StaticAdapter(ModelAdapter):
    def __init__(self, reply: str) -> None:
        self.reply = reply

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del messages, model, max_tokens
        return self.reply, Decimal("0")


class _SequenceAdapter(ModelAdapter):
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del messages, model, max_tokens
        return self.replies.pop(0), Decimal("0")


class _CapturingAdapter(ModelAdapter):
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.messages: list[list[dict[str, Any]]] = []
        self.models: list[str] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del max_tokens
        self.messages.append(messages)
        self.models.append(model)
        return self.reply, Decimal("0")


class _FailingAdapter(ModelAdapter):
    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del messages, model, max_tokens
        raise RuntimeError("Unexpected content type from OpenRouter: <class 'NoneType'>")


class _FailingFleetSnapshotTool(Tool):
    name = "fleet.snapshot"
    description = "Failing fleet snapshot."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "profile_limit": {"type": "integer"},
            "period_days": {"type": "integer"},
        },
        "additionalProperties": False,
    }

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        del args, context
        raise RuntimeError("PFOS source packet unavailable: auth_redirect_html")


class _AtlasProposalTool(Tool):
    name = "atlas.propose_action"
    description = "Test Atlas proposal tool."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }

    def __init__(self, *, ok: bool) -> None:
        self.ok = ok
        self.calls: list[dict[str, Any]] = []

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        self.calls.append(args)
        if not self.ok:
            return ToolResult(ok=False, output=None, error="receipt_unverified")
        return ToolResult(
            ok=True,
            output={
                "status": "proposed_only",
                "verified": True,
                "action_id": "a1",
                "event_id": "e1",
                "silo_slug": "prettyfly",
                "executed": False,
                "slack_card": {
                    "action_id": "a1",
                    "silo_slug": "prettyfly",
                    "title": "Approve Atlas weekly operating focus",
                    "summary": "Atlas found too many competing priorities.",
                    "priority": "high",
                    "risk_level": "medium",
                    "pfos_href": "/agents/atlas-ceo",
                },
            },
        )


class _AtlasFollowUpTool(Tool):
    name = "atlas.record_follow_up"
    description = "Test Atlas follow-up tool."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
        "additionalProperties": True,
    }

    def __init__(self, *, ok: bool) -> None:
        self.ok = ok
        self.calls: list[dict[str, Any]] = []

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        self.calls.append(args)
        if not self.ok:
            return ToolResult(ok=False, output=None, error="follow_up_event_unverified")
        return ToolResult(
            ok=True,
            output={
                "verified": True,
                "event_id": "ready-event-1",
                "status": "completed",
                "source_follow_up_event_id": "queued-event-1",
                "source_action_id": "action-1",
                "executed": False,
            },
        )


@pytest.mark.asyncio
async def test_atlas_blocks_unsourced_metric_claims(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="atlas-ceo", user_id="alex", text="brief"),
        model_adapter=_StaticAdapter("ARR is $2M and churn is 3%."),
    )

    assert "verified fleet source packet" in result.messages[-1].content
    assert "$2M" not in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_blocks_external_action_claims(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="atlas-ceo", user_id="alex", text="send"),
        model_adapter=_StaticAdapter("I sent the client update."),
    )

    assert "I cannot claim" in result.messages[-1].content
    assert "sent the client" not in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_blocks_proposal_recorded_claim_without_receipt(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_StaticAdapter("I recorded the decision proposal in PFOS."),
    )

    assert "do not have a verified PFOS proposal receipt" in result.messages[-1].content
    assert "recorded the decision proposal" not in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_blocks_follow_up_recorded_claim_without_receipt(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="write the approved decision follow-up brief",
        ),
        model_adapter=_StaticAdapter("I recorded the follow-up in PFOS."),
    )

    assert "do not have a verified PFOS follow-up event receipt" in result.messages[-1].content
    assert "recorded the follow-up" not in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_source_packet_failure_becomes_degraded_context(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    adapter = _CapturingAdapter("I do not have enough verified signal for a CEO brief.")

    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="give me this week CEO brief",
        ),
        model_adapter=adapter,
        tools=[_FailingFleetSnapshotTool()],
    )

    injected_context = json.dumps(adapter.messages[0], sort_keys=True)
    assert result.finish_reason == "stop"
    assert "atlas.source_packet.degraded" in injected_context
    assert "auth_redirect_html" in injected_context
    assert "not have enough verified signal" in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_uses_configured_premium_route_for_source_grounded_brief(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    (profile.env_path.parent / "config.yaml").write_text(
        "model:\n  routing:\n    source_grounded_brief: anthropic:claude-sonnet-4-6\n",
        encoding="utf-8",
    )
    adapter = _CapturingAdapter("Current constraint: choose one priority.")

    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="give me this week CEO brief",
        ),
        model_adapter=adapter,
        tools=[_FailingFleetSnapshotTool()],
    )

    assert result.finish_reason == "stop"
    assert adapter.models == ["anthropic:claude-sonnet-4-6"]


@pytest.mark.asyncio
async def test_atlas_model_adapter_failure_returns_degraded_answer(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")

    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="atlas-ceo", user_id="alex", text="brief"),
        model_adapter=_FailingAdapter(),
    )

    assert result.finish_reason == "model_error"
    assert "could not complete the model call" in result.messages[-1].content
    assert "No action was recorded or executed" in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_blocks_proposal_recorded_claim_after_failed_tool(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_SequenceAdapter(
            [
                json.dumps(
                    {
                        "tool_call": {
                            "name": "atlas.propose_action",
                            "arguments": {},
                        }
                    }
                ),
                "I recorded the decision proposal in PFOS.",
            ]
        ),
        tools=[_AtlasProposalTool(ok=False)],
    )

    assert "do not have a verified PFOS proposal receipt" in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_blocks_hallucinated_tool_json_and_receipt(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_SequenceAdapter(
            [
                '{"tool_call":{"name":"atlas.propose_action","arguments":{}}} '
                '{"action_id":"fake","event_id":"fake","status":"proposed"}',
                "Recorded PFOS proposal action_id=fake event_id=fake.",
            ]
        ),
        tools=[_AtlasProposalTool(ok=False)],
    )

    assert "do not have a verified PFOS proposal receipt" in result.messages[-1].content
    assert "action_id=fake" not in result.messages[-1].content


@pytest.mark.asyncio
async def test_atlas_adds_degraded_model_metadata_to_proposal_tool_call(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    tool = _AtlasProposalTool(ok=False)

    await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_SequenceAdapter(
            [
                '[DEGRADED_MODEL_ROUTE]\n{"tool_call":{"name":"atlas.propose_action","arguments":{}}}',
                "I drafted the recommendation only.",
            ]
        ),
        tools=[tool],
    )

    assert tool.calls[0]["model_route_status"] == "degraded"
    assert tool.calls[0]["model_route_degraded"] is True


@pytest.mark.asyncio
async def test_atlas_allows_proposal_recorded_claim_with_verified_receipt(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="cli",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_SequenceAdapter(
            [
                json.dumps(
                    {
                        "tool_call": {
                            "name": "atlas.propose_action",
                            "arguments": {},
                        }
                    }
                ),
                "I recorded the decision proposal in PFOS as action a1.",
            ]
        ),
        tools=[_AtlasProposalTool(ok=True)],
    )

    assert result.messages[-1].content == "I recorded the decision proposal in PFOS as action a1."


@pytest.mark.asyncio
async def test_atlas_verified_receipt_exposes_slack_decision_card_metadata(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="slack",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_SequenceAdapter(
            [
                json.dumps(
                    {
                        "tool_call": {
                            "name": "atlas.propose_action",
                            "arguments": {},
                        }
                    }
                ),
                "I recorded the decision proposal in PFOS as action a1.",
            ]
        ),
        tools=[_AtlasProposalTool(ok=True)],
    )

    card = result.metadata["atlas_slack_decision_card"]
    assert card["action_id"] == "a1"
    assert card["silo_slug"] == "prettyfly"
    assert card["title"] == "Approve Atlas weekly operating focus"


@pytest.mark.asyncio
async def test_atlas_failed_receipt_exposes_no_slack_decision_card_metadata(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="slack",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="create an approval proposal",
        ),
        model_adapter=_SequenceAdapter(
            [
                json.dumps(
                    {
                        "tool_call": {
                            "name": "atlas.propose_action",
                            "arguments": {},
                        }
                    }
                ),
                "I drafted the recommendation only.",
            ]
        ),
        tools=[_AtlasProposalTool(ok=False)],
    )

    assert "atlas_slack_decision_card" not in result.metadata


@pytest.mark.asyncio
async def test_atlas_follow_up_uses_source_packet_and_record_tool(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    adapter = _SequenceAdapter(
        [
            json.dumps(
                {
                    "tool_call": {
                        "name": "atlas.record_follow_up",
                        "arguments": {
                            "source_follow_up_event_id": "queued-event-1",
                            "source_action_id": "action-1",
                            "approved_decision_title": "Approve Atlas focus",
                            "next_action": "Alex confirms the focus.",
                            "watch_item": "Watch the pending queue.",
                            "non_action": "Do not dispatch.",
                            "review_timing": "Review in 24h.",
                            "confidence": 0.82,
                        },
                    }
                }
            ),
            (
                "Approved decision: Approve Atlas focus\n"
                "Next action for Alex: Confirm the focus.\n"
                "What Atlas is watching: Pending queue.\n"
                "What not to do: Do not dispatch.\n"
                "Review timing: Review in 24h.\n"
                "Follow-up recorded in PFOS as ready-event-1."
            ),
        ]
    )

    result = await run_session(
        profile,
        InboundMessage(
            channel="slack",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="approved decision follow-up for atlas.follow_up.queued queued-event-1",
        ),
        model_adapter=adapter,
        tools=[_FailingFleetSnapshotTool(), _AtlasFollowUpTool(ok=True)],
    )

    content = result.messages[-1].content
    assert "Approved decision:" in content
    assert "Next action for Alex:" in content
    assert "What Atlas is watching:" in content
    assert "What not to do:" in content
    assert "Review timing:" in content
    assert "Follow-up recorded" in content


@pytest.mark.asyncio
async def test_atlas_follow_up_final_answer_keeps_five_fields_when_model_is_terse(
    tmp_path: Path,
) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    adapter = _SequenceAdapter(
        [
            json.dumps(
                {
                    "tool_call": {
                        "name": "atlas.record_follow_up",
                        "arguments": {
                            "source_follow_up_event_id": "queued-event-1",
                            "source_action_id": "action-1",
                            "approved_decision_title": "Approve Atlas loop dogfood",
                            "next_action": "Alex reviews the queue outcome.",
                            "watch_item": "Watch for duplicate follow-ups.",
                            "non_action": "Do not execute approved work.",
                            "review_timing": "Review tomorrow morning.",
                            "confidence": 0.84,
                        },
                    }
                }
            ),
            "Follow-up recorded and verified. The five-field brief above stands.",
        ]
    )

    result = await run_session(
        profile,
        InboundMessage(
            channel="slack",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="approved decision follow-up for atlas.follow_up.queued queued-event-1",
        ),
        model_adapter=adapter,
        tools=[_FailingFleetSnapshotTool(), _AtlasFollowUpTool(ok=True)],
    )

    content = result.messages[-1].content
    assert "Approved decision: Approve Atlas loop dogfood" in content
    assert "Next action for Alex: Alex reviews the queue outcome." in content
    assert "What Atlas is watching: Watch for duplicate follow-ups." in content
    assert "What not to do: Do not execute approved work." in content
    assert "Review timing: Review tomorrow morning." in content
    assert "No execution, dispatch" in content


@pytest.mark.asyncio
async def test_atlas_follow_up_failed_tool_blocks_recorded_claim(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "atlas-ceo")
    result = await run_session(
        profile,
        InboundMessage(
            channel="slack",
            profile_slug="atlas-ceo",
            user_id="alex",
            text="approved decision follow-up for atlas.follow_up.queued queued-event-1",
        ),
        model_adapter=_SequenceAdapter(
            [
                json.dumps(
                    {
                        "tool_call": {
                            "name": "atlas.record_follow_up",
                            "arguments": {},
                        }
                    }
                ),
                "I recorded the follow-up in PFOS.",
            ]
        ),
        tools=[_AtlasFollowUpTool(ok=False)],
    )

    assert "do not have a verified PFOS follow-up event receipt" in result.messages[-1].content


@pytest.mark.asyncio
async def test_guardrails_do_not_apply_to_other_profiles(tmp_path: Path) -> None:
    profile = _profile(tmp_path, "personal")
    result = await run_session(
        profile,
        InboundMessage(channel="cli", profile_slug="personal", user_id="alex", text="brief"),
        model_adapter=_StaticAdapter("ARR is $2M and churn is 3%."),
    )

    assert result.messages[-1].content == "ARR is $2M and churn is 3%."


def _profile(tmp_path: Path, slug: str) -> Profile:
    pdir = tmp_path / slug
    pdir.mkdir()
    for name in ("SOUL.md", "USER.md", "MEMORY.md", ".env"):
        (pdir / name).write_text("# x\n", encoding="utf-8")
    return Profile(
        slug=slug,
        model="x/y",
        provider="openrouter",
        soul_md_path=pdir / "SOUL.md",
        user_md_path=pdir / "USER.md",
        memory_md_path=pdir / "MEMORY.md",
        env_path=pdir / ".env",
    )
