"""PF Runtime tools for communications proposals."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

from pf_runtime.communications.proposal_store import ProposalStore
from pf_runtime.communications.schema import ActionType, ProposedAction
from pf_runtime.runtime.tool_dispatch import Tool, ToolContext, ToolResult


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
        },
        "additionalProperties": False,
    }

    def __init__(self, db_path: Path) -> None:
        self._store = ProposalStore(db_path)

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        del context
        action = ProposedAction(
            action_id=str(args["action_id"]),
            action_type=ActionType(str(args["action_type"])),
            account_id=str(args["account_id"]),
            target_id=str(args["target_id"]),
            rationale=str(args["rationale"]),
            payload=dict(args.get("payload") or {}),
        )
        proposal_id = self._store.add(action)
        return ToolResult(
            ok=True,
            output={"proposal_id": proposal_id, "status": "proposed"},
            cost_usd=Decimal("0"),
        )
