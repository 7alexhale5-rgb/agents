"""Postgres Kanban store — optional until DATABASE_URL is set."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4


@dataclass
class KanbanStore:
    """Async Kanban persistence; methods are no-ops when DSN is missing."""

    dsn: str | None

    @classmethod
    def from_env(cls) -> KanbanStore:
        return cls(dsn=os.environ.get("PF_KANBAN_DATABASE_URL") or os.environ.get("DATABASE_URL"))

    async def ping(self) -> bool:
        """Return True if asyncpg connects and schema is reachable."""
        if not self.dsn:
            return False
        try:
            import asyncpg
        except ImportError:
            return False
        try:
            conn = await asyncpg.connect(self.dsn)
            try:
                await conn.fetchval(
                    "SELECT to_regclass('public.pf_kanban_tasks')",
                )
            finally:
                await conn.close()
            return True
        except Exception:
            return False

    async def insert_task(
        self,
        *,
        profile_slug: str,
        title: str,
        body: str | None = None,
        status: str = "backlog",
    ) -> UUID | None:
        if not self.dsn:
            return None
        import asyncpg

        task_id = uuid4()
        conn = await asyncpg.connect(self.dsn)
        try:
            await conn.execute(
                """
                INSERT INTO pf_kanban_tasks (id, profile_slug, title, body, status)
                VALUES ($1, $2, $3, $4, $5)
                """,
                task_id,
                profile_slug,
                title,
                body,
                status,
            )
        finally:
            await conn.close()
        return task_id

    async def list_tasks(self, profile_slug: str, *, limit: int = 50) -> list[dict[str, Any]]:
        if not self.dsn:
            return []
        import asyncpg

        conn = await asyncpg.connect(self.dsn)
        try:
            rows = await conn.fetch(
                """
                SELECT id, title, body, status, created_at
                FROM pf_kanban_tasks
                WHERE profile_slug = $1
                ORDER BY updated_at DESC
                LIMIT $2
                """,
                profile_slug,
                limit,
            )
            return [dict(r) for r in rows]
        finally:
            await conn.close()
