"""Tier 2 memory — SQLite WAL-mode append-only message buffer.

One database file per profile slug, stored at:
    $PF_BUFFER_DIR/{slug}/pf_buffer.sqlite
    (default: ~/.hermes/profiles/{slug}/pf_buffer.sqlite)

Override the base directory via the ``buffer_dir`` constructor argument or
the ``PF_BUFFER_DIR`` environment variable. The env-var path takes
precedence over the constructor argument when both are provided.

Tier 4 isolation hard contract (THREAT_MODEL.md §Cross-tenant):
    - BufferStore refuses None or empty ``profile_slug`` at construction time.
    - All queries are pinned to self._profile_slug; no method accepts a
      different slug, making cross-profile access impossible by API design.

Schema (locked — do not change without amending MEMORY_LIFECYCLE.md):
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      profile_slug TEXT NOT NULL,
      session_id TEXT,
      role TEXT NOT NULL,
      content TEXT NOT NULL,
      timestamp REAL NOT NULL,
      created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
    );
    CREATE INDEX IF NOT EXISTS idx_messages_profile_ts
        ON messages(profile_slug, timestamp DESC);
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from types import TracebackType

from pf_runtime.config import Message

_DEFAULT_HERMES_HOME = Path.home() / ".hermes"

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_slug TEXT NOT NULL,
    session_id TEXT,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp REAL NOT NULL,
    created_at REAL NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_profile_ts
    ON messages(profile_slug, timestamp DESC);
"""


class BufferStore:
    """Per-profile SQLite WAL-mode message buffer.

    Usage (context-manager)::

        with BufferStore("personal") as buf:
            buf.append(msg)
            recent = buf.recent(limit=10)

    Or call ``open()`` / ``close()`` manually if a context manager is
    inconvenient.

    Args:
        profile_slug: Non-empty profile identifier. Raises ``ValueError``
            for None-or-empty values (Tier 4 isolation contract).
        buffer_dir: Base directory for buffer files. Defaults to
            ``~/.hermes/profiles`` (one sub-dir per slug). Overridden by
            the ``PF_BUFFER_DIR`` environment variable when set.
    """

    def __init__(
        self,
        profile_slug: str,
        buffer_dir: Path | None = None,
    ) -> None:
        # Tier 4 isolation hard contract — refuse empty / None slug.
        if not profile_slug:
            raise ValueError(
                "profile_slug must be a non-empty string (Tier 4 isolation contract)"
            )

        self._profile_slug: str = profile_slug

        # Resolve the database path:
        # 1. PF_BUFFER_DIR env var (highest priority)
        # 2. constructor buffer_dir argument
        # 3. default ~/.hermes/profiles/{slug}/
        env_dir = os.environ.get("PF_BUFFER_DIR")
        if env_dir:
            base = Path(env_dir)
        elif buffer_dir is not None:
            base = buffer_dir
        else:
            base = _DEFAULT_HERMES_HOME / "profiles" / profile_slug

        self._db_path: Path = base / "pf_buffer.sqlite"
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------ #
    # Connection lifecycle
    # ------------------------------------------------------------------ #

    def open(self) -> BufferStore:
        """Open the SQLite connection and ensure the schema exists."""
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        # Enable WAL for single-writer-multi-reader concurrency.
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()
        return self

    def close(self) -> None:
        """Close the SQLite connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> BufferStore:
        return self.open()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @property
    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError(
                "BufferStore is not open. "
                "Use 'with BufferStore(...) as buf:' or call buf.open() first."
            )
        return self._conn

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def append(self, message: Message, session_id: str | None = None) -> int:
        """INSERT a message into the buffer.

        Args:
            message: The Message to persist.
            session_id: Optional session identifier for grouping turns.

        Returns:
            The SQLite rowid of the inserted row.
        """
        ts = time.time()
        cur = self._connection.execute(
            """
            INSERT INTO messages (profile_slug, session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (self._profile_slug, session_id, message.role, message.content, ts),
        )
        self._connection.commit()
        return cur.lastrowid or 0

    def recent(
        self,
        limit: int = 10,
        before_ts: float | None = None,
    ) -> list[Message]:
        """Return the most-recent *limit* messages (timestamp DESC).

        Args:
            limit: Maximum number of messages to return.
            before_ts: When provided, only return messages with
                ``timestamp < before_ts``.

        Returns:
            List of Message objects, most-recent first.
        """
        if before_ts is not None:
            rows = self._connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE profile_slug = ? AND timestamp < ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (self._profile_slug, before_ts, limit),
            ).fetchall()
        else:
            rows = self._connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE profile_slug = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (self._profile_slug, limit),
            ).fetchall()

        return [Message(role=row["role"], content=row["content"]) for row in rows]

    def count(self) -> int:
        """Return the total number of messages stored for this profile."""
        row = self._connection.execute(
            "SELECT COUNT(*) FROM messages WHERE profile_slug = ?",
            (self._profile_slug,),
        ).fetchone()
        return int(row[0]) if row else 0
