"""Tests for the Phase 3 dedupe + dirty-flag additions on ProposalStore."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pf_runtime.communications.proposal_store import ProposalStore
from pf_runtime.communications.schema import ActionType, ProposedAction


def _action(account_id: str = "gmail-1", target_id: str = "msg-1") -> ProposedAction:
    return ProposedAction(
        action_id=f"{account_id}-{target_id}-reply",
        action_type=ActionType.REPLY_DRAFT,
        account_id=account_id,
        target_id=target_id,
        rationale="boss asked a direct question",
        payload={"thread_id": "t-1"},
        status="proposed",
        created_at=datetime.now(UTC),
    )


def test_phase3_columns_exist_after_init(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    _ = store  # silence unused
    with sqlite3.connect(tmp_path / "p.sqlite") as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(communications_proposals)")}
    assert {"also_seen_in", "also_seen_count", "dirty", "dedupe_key"} <= cols


def test_add_with_dedupe_key_records_it(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    store.add(_action(), dedupe_key="rfc822:<abc@example.com>")
    found = store.find_by_dedupe("rfc822:<abc@example.com>")
    assert found is not None
    assert found["account_id"] == "gmail-1"
    assert found["also_seen_in"] == ["gmail-1"]
    assert found["also_seen_count"] == 1


def test_find_by_dedupe_returns_none_for_missing(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    store.add(_action(), dedupe_key="rfc822:<one@x.com>")
    assert store.find_by_dedupe("rfc822:<other@x.com>") is None
    # Empty / null keys never match.
    assert store.find_by_dedupe("") is None


def test_append_also_seen_grows_list_and_bumps_count(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    store.add(_action("gmail-1"), dedupe_key="key")
    action_id = "gmail-1-msg-1-reply"
    new_count = store.append_also_seen(action_id, "gmail-2")
    assert new_count == 2
    found = store.find_by_dedupe("key")
    assert found is not None
    assert found["also_seen_in"] == ["gmail-1", "gmail-2"]
    assert found["also_seen_count"] == 2


def test_append_also_seen_is_idempotent_on_same_account(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    store.add(_action("gmail-1"), dedupe_key="key")
    store.append_also_seen("gmail-1-msg-1-reply", "gmail-2")
    # Re-appending gmail-2 should not double-count.
    count = store.append_also_seen("gmail-1-msg-1-reply", "gmail-2")
    assert count == 2


def test_append_also_seen_raises_keyerror_for_unknown_action(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    with pytest.raises(KeyError):
        store.append_also_seen("nonexistent", "gmail-1")


def test_mark_dirty_toggles_flag(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    store.add(_action(), dedupe_key="k")
    store.mark_dirty("gmail-1-msg-1-reply", True)
    with sqlite3.connect(tmp_path / "p.sqlite") as conn:
        row = conn.execute(
            "SELECT dirty FROM communications_proposals WHERE action_id = ?",
            ("gmail-1-msg-1-reply",),
        ).fetchone()
    assert row[0] == 1
    store.mark_dirty("gmail-1-msg-1-reply", False)
    with sqlite3.connect(tmp_path / "p.sqlite") as conn:
        row = conn.execute(
            "SELECT dirty FROM communications_proposals WHERE action_id = ?",
            ("gmail-1-msg-1-reply",),
        ).fetchone()
    assert row[0] == 0


def test_mark_dirty_raises_keyerror_for_unknown_action(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "p.sqlite")
    with pytest.raises(KeyError):
        store.mark_dirty("nonexistent", True)


def test_init_is_idempotent_on_existing_db(tmp_path: Path) -> None:
    """A repeat ProposalStore() on the same path should not raise even
    when the Phase 3 columns already exist."""
    p = tmp_path / "p.sqlite"
    ProposalStore(p)
    ProposalStore(p)
    ProposalStore(p)
    # Smoke: confirm the dedupe index also exists.
    with sqlite3.connect(p) as conn:
        idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_communications_proposals_dedupe'"
        ).fetchone()
    assert idx is not None


def test_dedupe_round_trip_via_json(tmp_path: Path) -> None:
    """also_seen_in is stored as a JSON string; verify the on-disk
    representation round-trips through json.loads correctly."""
    store = ProposalStore(tmp_path / "p.sqlite")
    store.add(_action("gmail-1"), dedupe_key="key")
    store.append_also_seen("gmail-1-msg-1-reply", "gmail-2")
    store.append_also_seen("gmail-1-msg-1-reply", "koho-m365")
    with sqlite3.connect(tmp_path / "p.sqlite") as conn:
        row = conn.execute(
            "SELECT also_seen_in FROM communications_proposals WHERE action_id = ?",
            ("gmail-1-msg-1-reply",),
        ).fetchone()
    assert json.loads(row[0]) == ["gmail-1", "gmail-2", "koho-m365"]
