"""KanbanStore — no-DSN paths and mocked asyncpg."""
from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import Any

import pytest

from pf_runtime.kanban.store import KanbanStore


@pytest.mark.asyncio
async def test_ping_false_without_dsn() -> None:
    assert await KanbanStore(dsn=None).ping() is False


@pytest.mark.asyncio
async def test_ping_false_on_connect_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_connect(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("connection refused")

    monkeypatch.setitem(
        sys.modules,
        "asyncpg",
        SimpleNamespace(connect=fail_connect),
    )
    assert await KanbanStore(dsn="postgres://localhost/db").ping() is False


@pytest.mark.asyncio
async def test_ping_true_when_table_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Conn:
        closed = False

        async def fetchval(self, _q: str) -> str:
            return "pf_kanban_tasks"

        async def close(self) -> None:
            self.closed = True

    _conn = _Conn()

    async def _connect(_dsn: str) -> _Conn:
        return _conn

    monkeypatch.setitem(
        sys.modules,
        "asyncpg",
        SimpleNamespace(connect=_connect),
    )
    assert await KanbanStore(dsn="postgres://x").ping() is True


@pytest.mark.asyncio
async def test_insert_and_list_no_dsn() -> None:
    k = KanbanStore(dsn=None)
    assert await k.insert_task(profile_slug="p", title="t") is None
    assert await k.list_tasks("p") == []


@pytest.mark.asyncio
async def test_insert_task_with_mock_asyncpg(monkeypatch: pytest.MonkeyPatch) -> None:
    execute_calls: list[tuple[Any, ...]] = []

    class _Conn:
        async def execute(self, *args: Any) -> None:
            execute_calls.append(args)

        async def close(self) -> None:
            pass

    async def _connect(_dsn: str) -> _Conn:
        return _Conn()

    monkeypatch.setitem(
        sys.modules,
        "asyncpg",
        SimpleNamespace(connect=_connect),
    )
    k = KanbanStore(dsn="postgres://local/db")
    tid = await k.insert_task(profile_slug="s", title="Do thing", body="b", status="open")
    assert tid is not None
    assert execute_calls and "INSERT INTO pf_kanban_tasks" in execute_calls[0][0]


@pytest.mark.asyncio
async def test_list_tasks_with_mock_asyncpg(monkeypatch: pytest.MonkeyPatch) -> None:
    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "title": "a",
        "body": None,
        "status": "backlog",
        "created_at": None,
    }

    class _Conn:
        async def fetch(self, *args: Any) -> list[dict[str, Any]]:
            return [row]

        async def close(self) -> None:
            pass

    async def _connect(_dsn: str) -> _Conn:
        return _Conn()

    monkeypatch.setitem(
        sys.modules,
        "asyncpg",
        SimpleNamespace(connect=_connect),
    )
    out = await KanbanStore(dsn="postgres://local/db").list_tasks("s", limit=5)
    assert len(out) == 1
    assert out[0]["title"] == "a"
