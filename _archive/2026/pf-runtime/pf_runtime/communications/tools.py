"""PF Runtime tools for communications proposals."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

from pf_runtime.communications.proposal_store import ProposalStore
from pf_runtime.communications.schema import ActionType, ProposedAction
from pf_runtime.runtime.pfos_emit import emit_agent_event, runtime_proposal_payload
from pf_runtime.runtime.tool_dispatch import Tool, ToolContext, ToolResult

SKILL_SLUG = "communications-triage"
AGENT_SLUG = "personal"


class CreateProposalTool(Tool):
    name = "communications.propose_action"
    description = "Create a read/propose-only mail or calendar action for Alex review."
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "required": ["action_id", "action_type", "account_id", "target_id", "rationale"],
        "properties": {
            "action_id": {"type": "string", "minLength": 1},
            "action_type": {
                "type": "string",
                "enum": [a.value for a in ActionType],
            },
            "account_id": {"type": "string", "minLength": 1},
            "target_id": {"type": "string", "minLength": 1},
            "rationale": {"type": "string", "minLength": 1},
            "payload": {"type": "object"},
            "confidence_bucket": {
                "type": "string",
                "enum": ["high", "medium", "low"],
            },
        },
        "additionalProperties": False,
    }

    def __init__(self, db_path: Path) -> None:
        self._store = ProposalStore(db_path)

    @property
    def store(self) -> ProposalStore:
        """Expose the underlying store for cross-account dedupe lookups.

        Phase 3 triage paths need to read existing proposals (via
        ``find_by_dedupe``) BEFORE deciding whether to call ``invoke``,
        so the store is surfaced as a read-and-update handle. The tool
        envelope remains the canonical write path; direct mutation of
        the store outside the tool should stay limited to dedupe
        bookkeeping (append_also_seen, mark_dirty).
        """
        return self._store

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        action = ProposedAction(
            action_id=str(args["action_id"]),
            action_type=ActionType(str(args["action_type"])),
            account_id=str(args["account_id"]),
            target_id=str(args["target_id"]),
            rationale=str(args["rationale"]),
            payload=dict(args.get("payload") or {}),
        )
        dedupe_key = args.get("dedupe_key")
        dedupe_key_str = str(dedupe_key) if dedupe_key else None
        proposal_id = self._store.add(action, dedupe_key=dedupe_key_str)

        confidence_bucket = args.get("confidence_bucket")
        confidence_str = str(confidence_bucket) if confidence_bucket else None

        # Fire-and-forget PFOS agent_event. No-op when env not configured;
        # transport errors logged inside emit. Storing the proposal locally is
        # the source of truth — emission is observability only.
        await emit_agent_event(
            runtime_proposal_payload(
                profile_slug=context.profile_slug or AGENT_SLUG,
                skill_slug=SKILL_SLUG,
                agent_slug=AGENT_SLUG,
                action_id=action.action_id,
                action_type=action.action_type.value,
                account_id=action.account_id,
                target_id=action.target_id,
                rationale_preview=action.rationale,
                confidence_bucket=confidence_str,
                session_id=context.session_id or None,
                trace_id=context.langfuse_trace_id or None,
                parent_run_id=context.session_id or None,
            )
        )

        return ToolResult(
            ok=True,
            output={"proposal_id": proposal_id, "status": "proposed"},
            cost_usd=Decimal("0"),
        )
