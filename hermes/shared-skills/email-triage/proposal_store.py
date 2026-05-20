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

# Phase 3 additive columns (cross-account dedupe + emit retry flag). Each
# ALTER is wrapped in a try/except IntegrityError; SQLite raises
# OperationalError on a duplicate column add, so we suppress that and
# carry on idempotently. The PRAGMA check below is the safe pre-flight.
_PHASE3_ADDITIONS: tuple[tuple[str, str], ...] = (
    ("also_seen_in", "TEXT NOT NULL DEFAULT '[]'"),
    ("also_seen_count", "INTEGER NOT NULL DEFAULT 1"),
    ("dirty", "INTEGER NOT NULL DEFAULT 0"),
    ("dedupe_key", "TEXT"),
)

_PHASE3_INDEX = """
CREATE INDEX IF NOT EXISTS idx_communications_proposals_dedupe
    ON communications_proposals(dedupe_key)
    WHERE dedupe_key IS NOT NULL;
"""


class ProposalStore:
    """Durable local store for proposed communications actions."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)
            # Idempotently add Phase 3 columns. SQLite's PRAGMA reports
            # the current column list; we only ALTER for the missing ones.
            existing_columns = {
                row[1]  # cid, name, type, notnull, dflt_value, pk
                for row in conn.execute(
                    "PRAGMA table_info(communications_proposals)"
                )
            }
            for column, defn in _PHASE3_ADDITIONS:
                if column not in existing_columns:
                    conn.execute(
                        f"ALTER TABLE communications_proposals "
                        f"ADD COLUMN {column} {defn}"
                    )
            conn.execute(_PHASE3_INDEX)
            conn.commit()

    def add(self, action: ProposedAction, *, dedupe_key: str | None = None) -> str:
        assert_v1_action_allowed(action, applying=False)
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO communications_proposals
                    (action_id, action_type, account_id, target_id, rationale,
                     payload_json, status, created_at,
                     also_seen_in, also_seen_count, dirty, dedupe_key)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    json.dumps([action.account_id]),
                    1,
                    0,
                    dedupe_key,
                ),
            )
            conn.commit()
        return action.action_id

    def find_by_dedupe(self, dedupe_key: str) -> dict[str, object] | None:
        """Return the first existing proposal whose dedupe_key matches.

        Used by triage_skill to collapse cross-account duplicates: when
        the same thread reaches alex@ and info@ within a window, the
        second cycle's hit appends ``account_id`` to ``also_seen_in``
        rather than inserting a second row.

        Returns ``None`` when no match — caller proceeds to insert.
        """
        if not dedupe_key:
            return None
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT action_id, account_id, also_seen_in, also_seen_count
                FROM communications_proposals
                WHERE dedupe_key = ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (dedupe_key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "action_id": str(row["action_id"]),
            "account_id": str(row["account_id"]),
            "also_seen_in": json.loads(str(row["also_seen_in"])),
            "also_seen_count": int(row["also_seen_count"]),
        }

    def append_also_seen(self, action_id: str, account_id: str) -> int:
        """Append ``account_id`` to the action's ``also_seen_in`` array.

        Returns the new ``also_seen_count``. Idempotent on the same
        ``account_id``: re-appending an already-listed account is a
        no-op (count stays). Raises ``KeyError`` when ``action_id`` is
        absent.
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT also_seen_in FROM communications_proposals WHERE action_id = ?",
                (action_id,),
            ).fetchone()
            if row is None:
                raise KeyError(action_id)
            seen: list[str] = list(json.loads(str(row["also_seen_in"])))
            if account_id in seen:
                return len(seen)
            seen.append(account_id)
            conn.execute(
                """
                UPDATE communications_proposals
                SET also_seen_in = ?, also_seen_count = ?
                WHERE action_id = ?
                """,
                (json.dumps(seen), len(seen), action_id),
            )
            conn.commit()
            return len(seen)

    def mark_dirty(self, action_id: str, dirty: bool) -> None:
        """Flag the row for emit retry on the next cycle (or clear it).

        PFOS emit failures mark the row dirty=1; the next cycle's
        drain step retries dirty rows before processing new messages.
        Idempotent — no-ops if the row is already in the target state.
        """
        with sqlite3.connect(self._db_path) as conn:
            cur = conn.execute(
                "UPDATE communications_proposals SET dirty = ? WHERE action_id = ?",
                (1 if dirty else 0, action_id),
            )
            if cur.rowcount != 1:
                raise KeyError(action_id)
            conn.commit()

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
