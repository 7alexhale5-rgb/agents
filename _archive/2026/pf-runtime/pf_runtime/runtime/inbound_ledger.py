"""Cross-restart inbound + outbound dedup for Slack (and future channels)."""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path


class SqliteInboundLedger:
    """SQLite-backed inbound claims and successful outbound posts."""

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inbound_keys (
                    k TEXT PRIMARY KEY,
                    seen_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS outbound_keys (
                    k TEXT PRIMARY KEY,
                    sent_at REAL NOT NULL
                )
                """
            )
            conn.commit()

    def try_claim(self, key: str) -> bool:
        if not key:
            return True
        now = time.time()
        try:
            with sqlite3.connect(self._path) as conn:
                conn.execute(
                    "INSERT INTO inbound_keys (k, seen_at) VALUES (?, ?)",
                    (key, now),
                )
                conn.commit()
        except sqlite3.IntegrityError:
            return False
        return True

    def outbound_already_sent(self, key: str) -> bool:
        """Return True if we already recorded a successful post for this key."""
        if not key:
            return False
        with sqlite3.connect(self._path) as conn:
            row = conn.execute(
                "SELECT 1 FROM outbound_keys WHERE k = ? LIMIT 1",
                (key,),
            ).fetchone()
        return row is not None

    def record_outbound_sent(self, key: str) -> None:
        """Record after a successful upstream send (idempotent insert)."""
        if not key:
            return
        now = time.time()
        with sqlite3.connect(self._path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO outbound_keys (k, sent_at) VALUES (?, ?)",
                (key, now),
            )
            conn.commit()
