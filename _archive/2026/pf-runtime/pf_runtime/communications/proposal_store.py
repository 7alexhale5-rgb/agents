"""SQLite proposal store for communications triage."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from pf_runtime.communications.policy import assert_v1_action_allowed
from pf_runtime.communications.schema import ActionType, ProposedAction

_SCHEMA = """
CREATE TABLE IF NOT EXISTS communications_proposals (
    action_id TEXT PRIMARY KEY,
    action_type TEXT NOT NULL,
    account_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    rationale TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_communications_proposals_status
    ON communications_proposals(status, created_at DESC);
"""


class ProposalStore:
    """Durable local store for proposed communications actions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def add(self, action: ProposedAction) -> str:
        assert_v1_action_allowed(action, applying=False)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO communications_proposals
                    (action_id, action_type, account_id, target_id, rationale,
                     payload_json, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.action_id,
                    action.action_type.value,
                    action.account_id,
                    action.target_id,
                    action.rationale,
                    json.dumps(action.payload, sort_keys=True),
                    action.status,
                    action.created_at.isoformat(),
                ),
            )
            conn.commit()
        return action.action_id

    def list(self, *, status: str = "proposed", limit: int = 100) -> list[ProposedAction]:
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT *
                FROM communications_proposals
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, limit),
            ).fetchall()
        return [
            ProposedAction(
                action_id=str(r["action_id"]),
                action_type=ActionType(str(r["action_type"])),
                account_id=str(r["account_id"]),
                target_id=str(r["target_id"]),
                rationale=str(r["rationale"]),
                payload=json.loads(str(r["payload_json"])),
                status=str(r["status"]),
                created_at=datetime.fromisoformat(str(r["created_at"])),
            )
            for r in rows
        ]

    def mark_reviewed(self, action_id: str, *, status: str) -> None:
        if status not in {"approved", "rejected"}:
            raise ValueError("status must be approved or rejected")
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute(
                "UPDATE communications_proposals SET status = ? WHERE action_id = ?",
                (status, action_id),
            )
            if cur.rowcount != 1:
                raise KeyError(action_id)
            conn.commit()
