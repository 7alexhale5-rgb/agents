"""CreateProposalTool emits an ARTIFACT_CREATED PFOS agent_event after store.add (Slice 4).

The store remains the source of truth; emission is observability only. When
PFOS_AGENT_EVENT_URL/TOKEN env vars are unset, the emit becomes a no-op
and the tool still succeeds.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from pf_runtime.communications import tools as tools_module
from pf_runtime.communications.tools import (
    AGENT_SLUG,
    SKILL_SLUG,
    CreateProposalTool,
)
from pf_runtime.runtime.pfos_emit import runtime_proposal_payload
from pf_runtime.runtime.tool_dispatch import ToolContext


@pytest.mark.asyncio
async def test_invoke_emits_artifact_created_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict[str, Any]] = []

    async def fake_emit(payload: dict[str, Any]) -> bool:
        captured.append(dict(payload))
        return True

    monkeypatch.setattr(tools_module, "emit_agent_event", fake_emit)

    tool = CreateProposalTool(tmp_path / "communications.sqlite")
    result = await tool.invoke(
        {
            "action_id": "p1",
            "action_type": "reply_draft",
            "account_id": "gmail-1",
            "target_id": "m1",
            "rationale": "needs Alex today: Q2 board update",
            "payload": {"draft": "Thanks, I will review."},
            "confidence_bucket": "high",
        },
        ToolContext(
            profile_slug="personal",
            session_id="sess-abc",
            langfuse_trace_id="trace-xyz",
        ),
    )

    assert result.ok is True
    assert result.output == {"proposal_id": "p1", "status": "proposed"}
    assert result.cost_usd == Decimal("0")

    assert len(captured) == 1
    payload = captured[0]
    assert payload["type"] == "ARTIFACT_CREATED"
    assert payload["surface"] == "pf_runtime"
    assert payload["agent_slug"] == AGENT_SLUG
    assert payload["skill_slug"] == SKILL_SLUG
    assert payload["cwd_project"] == "personal"
    assert payload["status"] == "pending"
    assert payload["trace_id"] == "trace-xyz"
    assert payload["parent_run_id"] == "sess-abc"

    data = payload["data"]
    assert data["kind"] == "pf_runtime_proposal"
    assert data["action_id"] == "p1"
    assert data["action_type"] == "reply_draft"
    assert data["account_id"] == "gmail-1"
    assert data["target_id"] == "m1"
    assert data["confidence_bucket"] == "high"
    assert data["session_id"] == "sess-abc"
    assert "needs Alex today" in data["rationale_preview"]


@pytest.mark.asyncio
async def test_invoke_succeeds_when_emit_unconfigured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No PFOS env -> emit_agent_event returns False; tool still succeeds."""
    monkeypatch.delenv("PFOS_AGENT_EVENT_URL", raising=False)
    monkeypatch.delenv("PFOS_AGENT_EVENT_TOKEN", raising=False)

    tool = CreateProposalTool(tmp_path / "communications.sqlite")
    result = await tool.invoke(
        {
            "action_id": "p1",
            "action_type": "label",
            "account_id": "gmail-1",
            "target_id": "m1",
            "rationale": "newsletter pile",
        },
        ToolContext(profile_slug="personal", session_id="s"),
    )
    assert result.ok is True
    assert result.output == {"proposal_id": "p1", "status": "proposed"}


def test_proposal_payload_truncates_rationale() -> None:
    long = "x" * 1500
    payload = runtime_proposal_payload(
        profile_slug="personal",
        skill_slug=SKILL_SLUG,
        agent_slug=AGENT_SLUG,
        action_id="p1",
        action_type="reply_draft",
        account_id="gmail-1",
        target_id="m1",
        rationale_preview=long,
    )
    assert len(payload["data"]["rationale_preview"]) == 500


def test_proposal_payload_omits_optional_fields_when_absent() -> None:
    payload = runtime_proposal_payload(
        profile_slug="personal",
        skill_slug=SKILL_SLUG,
        agent_slug=AGENT_SLUG,
        action_id="p1",
        action_type="archive",
        account_id="gmail-1",
        target_id="m1",
        rationale_preview="quick",
    )
    assert "trace_id" not in payload
    assert "parent_run_id" not in payload
    assert "confidence_bucket" not in payload["data"]
    assert "session_id" not in payload["data"]
    assert payload["status"] == "pending"
