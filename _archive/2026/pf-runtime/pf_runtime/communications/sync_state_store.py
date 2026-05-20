"""SQLite per-account sync state store for communications triage.

Tracks the cursor each provider needs to resume incremental sync:
* Gmail history-id (``history_id``)
* Microsoft Graph delta link (``delta_link``)
* IMAP UID watermark + UIDVALIDITY (``last_uid`` / ``uid_validity``)

Mirrors the pattern in :mod:`proposal_store` so the sync state and the
proposal queue can share the same SQLite file. The schema is idempotent:
``__init__`` is safe to call repeatedly against an existing DB.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path

from pf_runtime.communications.schema import Provider

_SCHEMA = """
CREATE TABLE IF NOT EXISTS communications_sync_state (
    account_id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    history_id TEXT,
    delta_link TEXT,
    last_uid INTEGER,
    uid_validity INTEGER,
    last_synced_at TEXT NOT NULL,
    last_error TEXT,
    last_error_at TEXT
);
"""


@dataclass(frozen=True)
class SyncState:
    """One row of ``communications_sync_state`` as a frozen value object."""

    account_id: str
    provider: Provider
    last_synced_at: datetime
    history_id: str | None = None
    delta_link: str | None = None
    last_uid: int | None = None
    uid_validity: int | None = None
    last_error: str | None = None
    last_error_at: datetime | None = None


class SyncStateStore:
    """Durable local store for per-account incremental-sync cursors."""

    def __init__(self, path: Path | str) -> None:
        self._db_path = Path(path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._db_path) as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    def get(self, account_id: str) -> SyncState | None:
        """Return the row for ``account_id`` or ``None``."""
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM communications_sync_state WHERE account_id = ?",
                (account_id,),
            ).fetchone()
        if row is None:
            return None
        return _row_to_state(row)

    def upsert(self, state: SyncState) -> None:
        """INSERT OR REPLACE the row keyed by ``state.account_id``."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO communications_sync_state
                    (account_id, provider, history_id, delta_link,
                     last_uid, uid_validity, last_synced_at,
                     last_error, last_error_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    state.account_id,
                    state.provider.value,
                    state.history_id,
                    state.delta_link,
                    state.last_uid,
                    state.uid_validity,
                    state.last_synced_at.isoformat(),
                    state.last_error,
                    state.last_error_at.isoformat() if state.last_error_at else None,
                ),
            )
            conn.commit()

    def mark_error(self, account_id: str, provider: Provider, error: str) -> None:
        """Record ``error`` against ``account_id`` without touching cursors.

        Preserves any existing cursor (history_id / delta_link / last_uid)
        so a transient failure does not force a full resync on next run.
        """
        existing = self.get(account_id)
        now = datetime.now(UTC)
        if existing is None:
            new_state = SyncState(
                account_id=account_id,
                provider=provider,
                last_synced_at=now,
                last_error=error,
                last_error_at=now,
            )
        else:
            new_state = replace(
                existing,
                last_error=error,
                last_error_at=now,
            )
        self.upsert(new_state)


def _row_to_state(row: sqlite3.Row) -> SyncState:
    raw_error_at = row["last_error_at"]
    return SyncState(
        account_id=str(row["account_id"]),
        provider=Provider(str(row["provider"])),
        history_id=str(row["history_id"]) if row["history_id"] is not None else None,
        delta_link=str(row["delta_link"]) if row["delta_link"] is not None else None,
        last_uid=int(row["last_uid"]) if row["last_uid"] is not None else None,
        uid_validity=(
            int(row["uid_validity"]) if row["uid_validity"] is not None else None
        ),
        last_synced_at=datetime.fromisoformat(str(row["last_synced_at"])),
        last_error=str(row["last_error"]) if row["last_error"] is not None else None,
        last_error_at=(
            datetime.fromisoformat(str(raw_error_at)) if raw_error_at is not None else None
        ),
    )
