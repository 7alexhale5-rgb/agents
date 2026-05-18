"""Sync state store tests (Slice 2).

Round-trip per provider, idempotent upsert, ``mark_error`` preserves cursor,
and datetime values survive ISO8601 round-trip.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from pf_runtime.communications.schema import Provider
from pf_runtime.communications.sync_state_store import SyncState, SyncStateStore


def _store(tmp_path: Path) -> SyncStateStore:
    return SyncStateStore(tmp_path / "comms.db")


def test_get_returns_none_for_unknown(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert store.get("missing") is None


def test_round_trip_gmail_history_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 5, 8, 12, 0, tzinfo=UTC)
    state = SyncState(
        account_id="gmail-1",
        provider=Provider.GOOGLE_MAIL,
        history_id="998877",
        last_synced_at=now,
    )
    store.upsert(state)
    fetched = store.get("gmail-1")
    assert fetched is not None
    assert fetched.account_id == "gmail-1"
    assert fetched.provider is Provider.GOOGLE_MAIL
    assert fetched.history_id == "998877"
    assert fetched.last_synced_at == now
    assert fetched.delta_link is None
    assert fetched.last_uid is None


def test_round_trip_graph_delta_link(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 5, 8, 13, 0, tzinfo=UTC)
    delta = "https://graph.microsoft.com/v1.0/me/.../delta?token=abc"
    store.upsert(
        SyncState(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            delta_link=delta,
            last_synced_at=now,
        )
    )
    fetched = store.get("graph-1")
    assert fetched is not None
    assert fetched.delta_link == delta
    assert fetched.history_id is None


def test_round_trip_imap_uid_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 5, 8, 14, 0, tzinfo=UTC)
    store.upsert(
        SyncState(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            last_uid=421,
            uid_validity=100100,
            last_synced_at=now,
        )
    )
    fetched = store.get("imap-1")
    assert fetched is not None
    assert fetched.last_uid == 421
    assert fetched.uid_validity == 100100


def test_upsert_replaces_existing_row(tmp_path: Path) -> None:
    store = _store(tmp_path)
    now = datetime(2026, 5, 8, 15, 0, tzinfo=UTC)
    later = datetime(2026, 5, 8, 16, 0, tzinfo=UTC)
    store.upsert(
        SyncState(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,
            history_id="1",
            last_synced_at=now,
        )
    )
    store.upsert(
        SyncState(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,
            history_id="2",
            last_synced_at=later,
        )
    )
    fetched = store.get("gmail-1")
    assert fetched is not None
    assert fetched.history_id == "2"
    assert fetched.last_synced_at == later


def test_mark_error_preserves_cursor(tmp_path: Path) -> None:
    store = _store(tmp_path)
    initial = SyncState(
        account_id="gmail-1",
        provider=Provider.GOOGLE_MAIL,
        history_id="42",
        last_synced_at=datetime(2026, 5, 8, 12, 0, tzinfo=UTC),
    )
    store.upsert(initial)
    store.mark_error("gmail-1", Provider.GOOGLE_MAIL, "boom")
    fetched = store.get("gmail-1")
    assert fetched is not None
    assert fetched.history_id == "42"  # cursor preserved
    assert fetched.last_error == "boom"
    assert fetched.last_error_at is not None
    assert fetched.last_error_at.tzinfo is not None


def test_mark_error_inserts_when_no_prior_state(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.mark_error("graph-1", Provider.MICROSOFT_GRAPH, "first failure")
    fetched = store.get("graph-1")
    assert fetched is not None
    assert fetched.last_error == "first failure"
    assert fetched.history_id is None
    assert fetched.delta_link is None


def test_init_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "comms.db"
    SyncStateStore(db)
    SyncStateStore(db)  # should not raise (CREATE TABLE IF NOT EXISTS)
    # Sanity: still works after the second init.
    store = SyncStateStore(db)
    store.upsert(
        SyncState(
            account_id="x",
            provider=Provider.GOOGLE_MAIL,
            last_synced_at=datetime.now(UTC),
        )
    )
    assert store.get("x") is not None


def test_iso8601_round_trip_for_error_timestamp(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.mark_error("imap-1", Provider.IMAP_HOSTGATOR, "fail")
    state = store.get("imap-1")
    assert state is not None
    assert state.last_error_at is not None
    # Round-trip property: re-saving the fetched row preserves the timestamp.
    store.upsert(state)
    again = store.get("imap-1")
    assert again is not None
    assert again.last_error_at == state.last_error_at


def test_init_accepts_str_path(tmp_path: Path) -> None:
    SyncStateStore(str(tmp_path / "comms.db"))


def test_get_after_only_mark_error_has_provider(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.mark_error("graph-1", Provider.MICROSOFT_GRAPH, "transient")
    fetched = store.get("graph-1")
    assert fetched is not None
    assert fetched.provider is Provider.MICROSOFT_GRAPH


@pytest.mark.parametrize(
    "provider",
    [Provider.GOOGLE_MAIL, Provider.MICROSOFT_GRAPH, Provider.IMAP_HOSTGATOR],
)
def test_provider_round_trips(tmp_path: Path, provider: Provider) -> None:
    store = _store(tmp_path)
    store.upsert(
        SyncState(
            account_id=f"acct-{provider.value}",
            provider=provider,
            last_synced_at=datetime.now(UTC),
        )
    )
    fetched = store.get(f"acct-{provider.value}")
    assert fetched is not None
    assert fetched.provider is provider
