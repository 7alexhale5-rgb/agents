"""Tier 2 BufferStore smoke tests.

Uses a temp dir for the SQLite file (via PF_BUFFER_DIR env var or constructor arg).
No mocking — real SQLite.

Tests:
  1. 100-message insert → zero lost writes (count == 100).
  2. recent(limit=10) returns most-recent-first (timestamp DESC).
  3. WAL mode is enabled.
  4. BufferStore("") raises ValueError (Tier 4 isolation contract).
  5. BufferStore(None) raises TypeError or ValueError.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from pf_runtime.config import Message
from pf_runtime.memory.tier2_buffer import BufferStore


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def buffer(tmp_path: Path) -> "BufferStore":  # type: ignore[return]
    """Return an open BufferStore pointing to a temp dir."""
    store = BufferStore("test-profile", buffer_dir=tmp_path)
    store.open()
    yield store  # type: ignore[misc]
    store.close()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestBufferStoreIsolation:
    """Tier 4 isolation contract: refuse empty/None profile_slug."""

    def test_empty_slug_raises_value_error(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="non-empty string"):
            BufferStore("", buffer_dir=tmp_path)

    def test_none_slug_raises(self, tmp_path: Path) -> None:
        with pytest.raises((TypeError, ValueError)):
            BufferStore(None, buffer_dir=tmp_path)  # type: ignore[arg-type]


class TestBufferStoreWAL:
    """Asserts WAL journal mode is active."""

    def test_wal_mode_enabled(self, buffer: BufferStore) -> None:
        row = buffer._connection.execute("PRAGMA journal_mode").fetchone()
        assert row is not None
        assert row[0] == "wal", f"Expected WAL mode, got: {row[0]}"


class TestBufferStoreInsertAndCount:
    """Zero lost writes on 100-message corpus."""

    def test_100_messages_zero_lost(self, buffer: BufferStore) -> None:
        for i in range(100):
            role = "user" if i % 2 == 0 else "assistant"
            msg = Message(role=role, content=f"message {i}")
            buffer.append(msg)
        assert buffer.count() == 100, (
            f"Expected 100 messages; got {buffer.count()}"
        )

    def test_count_starts_at_zero(self, tmp_path: Path) -> None:
        with BufferStore("fresh-profile", buffer_dir=tmp_path) as buf:
            assert buf.count() == 0


class TestBufferStoreRecent:
    """recent() returns messages most-recent-first."""

    def test_recent_order_is_desc(self, buffer: BufferStore) -> None:
        """Insert 20 messages with distinct content; recent(10) must be the last 10 in DESC order."""
        contents = [f"msg-{i}" for i in range(20)]
        for content in contents:
            buffer.append(Message(role="user", content=content))
            time.sleep(0.001)  # ensure distinct timestamps

        recent = buffer.recent(limit=10)
        assert len(recent) == 10, f"Expected 10 messages; got {len(recent)}"

        # The most-recent message was "msg-19"
        assert recent[0].content == "msg-19", (
            f"First recent message should be most recent ('msg-19'), got: {recent[0].content}"
        )
        # The 10th most-recent message was "msg-10"
        assert recent[9].content == "msg-10", (
            f"Last of 10 should be 'msg-10', got: {recent[9].content}"
        )

    def test_recent_limit_respected(self, buffer: BufferStore) -> None:
        for i in range(50):
            buffer.append(Message(role="user", content=f"x{i}"))
        recent = buffer.recent(limit=5)
        assert len(recent) == 5

    def test_recent_empty_store_returns_empty_list(self, tmp_path: Path) -> None:
        with BufferStore("empty-profile", buffer_dir=tmp_path) as buf:
            assert buf.recent(limit=10) == []

    def test_recent_before_ts_filter(self, buffer: BufferStore) -> None:
        """Messages after a given timestamp should not appear when before_ts is set."""
        buffer.append(Message(role="user", content="early"))
        cutoff = time.time()
        time.sleep(0.01)
        buffer.append(Message(role="user", content="late"))

        results = buffer.recent(limit=10, before_ts=cutoff)
        contents = [m.content for m in results]
        assert "early" in contents
        assert "late" not in contents


class TestBufferStoreRolePreserved:
    """Role field must round-trip correctly."""

    def test_role_roundtrip(self, buffer: BufferStore) -> None:
        buffer.append(Message(role="user", content="hello"))
        buffer.append(Message(role="assistant", content="hi there"))
        recent = buffer.recent(limit=2)
        roles = {m.role for m in recent}
        assert roles == {"user", "assistant"}


class TestBufferStoreContextManager:
    """Context manager opens and closes connection cleanly."""

    def test_context_manager_lifecycle(self, tmp_path: Path) -> None:
        with BufferStore("ctx-profile", buffer_dir=tmp_path) as buf:
            buf.append(Message(role="user", content="test"))
            assert buf.count() == 1
        # After __exit__, the connection should be closed
        assert buf._conn is None

    def test_operations_after_close_raise(self, tmp_path: Path) -> None:
        store = BufferStore("closed-profile", buffer_dir=tmp_path)
        store.open()
        store.close()
        with pytest.raises(RuntimeError, match="not open"):
            store.count()


class TestBufferStoreCrossProfileIsolation:
    """Profile A's BufferStore cannot see Profile B's rows."""

    def test_cross_profile_isolation(self, tmp_path: Path) -> None:
        with BufferStore("profile-a", buffer_dir=tmp_path) as buf_a:
            buf_a.append(Message(role="user", content="profile-a-message"))

        with BufferStore("profile-b", buffer_dir=tmp_path) as buf_b:
            # profile-b was never written to — should have 0 messages
            assert buf_b.count() == 0
            recent = buf_b.recent(limit=10)
            assert not any(m.content == "profile-a-message" for m in recent)
