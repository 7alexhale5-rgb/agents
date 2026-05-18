"""HostGator IMAP client tests (Slice 2).

Uses a small in-process fake IMAP class injected via ``imap_factory``.
Covers transport rejection (port 143), EXAMINE-not-SELECT, UID polling
delta math, UIDVALIDITY change → resync, and the 100-message fetch cap.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from pf_runtime.communications.account_registry import (
    RegistryEntry,
    RegistryValidationError,
)
from pf_runtime.communications.clients.imap_hostgator import ImapHostgatorClient
from pf_runtime.communications.schema import AccountConfig, Provider
from pf_runtime.communications.sync_state_store import SyncState, SyncStateStore


def _entry(*, port: int = 993, ssl: bool = True, smtp: bool = False) -> RegistryEntry:
    from pf_runtime.communications.account_registry import IMAPSettings

    return RegistryEntry(
        account=AccountConfig(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            address="alex@yehovahbuilders.com",
            scopes=(),
            read_only=True,
        ),
        imap=IMAPSettings(port=port, ssl=ssl, smtp_enabled_v1=smtp),
        credentials_present=True,
    )


def _store(tmp_path: Path) -> SyncStateStore:
    return SyncStateStore(tmp_path / "comms.db")


# ---------------------------------------------------------------------------
# Fake IMAP server
# ---------------------------------------------------------------------------


def _build_rfc822(uid: int, subject: str = "test", *, body: str = "hello\n") -> bytes:
    return (
        f"From: someone@example.com\r\n"
        f"To: alex@yehovahbuilders.com\r\n"
        f"Subject: {subject}-{uid}\r\n"
        f"Date: Thu, 8 May 2026 12:00:00 +0000\r\n"
        f"Message-Id: <{uid}@example.com>\r\n"
        f"Content-Type: text/plain; charset=utf-8\r\n"
        f"\r\n"
        f"{body}"
    ).encode()


class FakeImap:
    """Minimal stand-in for imaplib.IMAP4_SSL — just enough for the client."""

    def __init__(self, *, uids: list[int], uid_validity: int) -> None:
        self._uids = sorted(uids)
        self._uid_validity = uid_validity
        self.calls: list[tuple[str, tuple[Any, ...]]] = []
        self.examined: bool = False
        self.selected: bool = False
        self.logged_in: bool = False
        self.logged_out: bool = False

    def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
        self.calls.append(("login", (user, password)))
        self.logged_in = True
        return ("OK", [b"logged in"])

    def select(self, mailbox: str = "INBOX") -> tuple[str, list[bytes]]:
        # Marker for the test: calling select() (vs examine) is a bug.
        self.calls.append(("select", (mailbox,)))
        self.selected = True
        return ("OK", [b"\\Seen-set"])

    def examine(self, mailbox: str = "INBOX") -> tuple[str, list[bytes]]:
        self.calls.append(("examine", (mailbox,)))
        self.examined = True
        return ("OK", [b"EXAMINE INBOX"])

    def response(self, key: str) -> tuple[str, list[bytes] | None]:
        if key == "UIDVALIDITY":
            return ("UIDVALIDITY", [str(self._uid_validity).encode("ascii")])
        return (key, None)

    def status(self, mailbox: str, names: str) -> tuple[str, list[bytes]]:
        return (
            "OK",
            [f'INBOX (UIDVALIDITY {self._uid_validity})'.encode("ascii")],
        )

    def uid(self, command: str, *args: Any) -> tuple[str, list[Any]]:
        self.calls.append(("uid", (command, args)))
        if command == "SEARCH":
            # imaplib's IMAP4.uid("SEARCH", None, "UID 5:*") → first arg None
            criteria = args[-1] if args else "ALL"
            uids = self._search(criteria)
            return ("OK", [" ".join(str(u) for u in uids).encode("ascii")])
        if command == "FETCH":
            uid = int(args[0])
            if uid not in self._uids:
                return ("OK", [None])
            return (
                "OK",
                [
                    (
                        f"{uid} (UID {uid} RFC822 {{...}}".encode("ascii"),
                        _build_rfc822(uid),
                    )
                ],
            )
        return ("OK", [b""])

    def _search(self, criteria: str) -> list[int]:
        if criteria == "ALL":
            return list(self._uids)
        if criteria.startswith("UID ") and ":" in criteria:
            range_part = criteria[len("UID ") :]
            lo_str, _hi_str = range_part.split(":", 1)
            lo = int(lo_str)
            return [u for u in self._uids if u >= lo]
        return []

    def logout(self) -> tuple[str, list[bytes]]:
        self.calls.append(("logout", ()))
        self.logged_out = True
        return ("BYE", [b"bye"])


# ---------------------------------------------------------------------------
# Construction-time refusal
# ---------------------------------------------------------------------------


def test_construction_refuses_port_143(tmp_path: Path) -> None:
    with pytest.raises(RegistryValidationError):
        ImapHostgatorClient(
            _entry(port=143, ssl=False),
            _store(tmp_path),
            password="pw",
            imap_factory=lambda: FakeImap(uids=[1], uid_validity=1),
        )


def test_construction_refuses_ssl_false(tmp_path: Path) -> None:
    with pytest.raises(RegistryValidationError):
        ImapHostgatorClient(
            _entry(port=993, ssl=False),
            _store(tmp_path),
            password="pw",
            imap_factory=lambda: FakeImap(uids=[1], uid_validity=1),
        )


def test_construction_refuses_smtp_enabled(tmp_path: Path) -> None:
    with pytest.raises(RegistryValidationError):
        ImapHostgatorClient(
            _entry(smtp=True),
            _store(tmp_path),
            password="pw",
            imap_factory=lambda: FakeImap(uids=[1], uid_validity=1),
        )


def test_construction_refuses_missing_imap_settings(tmp_path: Path) -> None:
    bad = RegistryEntry(
        account=AccountConfig(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            address="x@y.com",
        ),
        imap=None,
        credentials_present=True,
    )
    with pytest.raises(RegistryValidationError):
        ImapHostgatorClient(bad, _store(tmp_path), password="pw")


def test_construction_requires_password(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ImapHostgatorClient(_entry(), _store(tmp_path), password="")


def test_construction_requires_correct_provider(tmp_path: Path) -> None:
    bad = RegistryEntry(
        account=AccountConfig(
            account_id="x",
            provider=Provider.GOOGLE_MAIL,
            address="x@example.com",
        ),
        credentials_present=True,
    )
    with pytest.raises(ValueError):
        ImapHostgatorClient(bad, _store(tmp_path), password="pw")


# ---------------------------------------------------------------------------
# fetch_new behaviour
# ---------------------------------------------------------------------------


def test_examine_used_not_select(tmp_path: Path) -> None:
    """The IMAP `\\Seen` flag must not be set — use EXAMINE, not SELECT."""
    fake = FakeImap(uids=[10, 11, 12], uid_validity=42)
    client = ImapHostgatorClient(
        _entry(),
        _store(tmp_path),
        password="pw",
        imap_factory=lambda: fake,
    )
    client.fetch_new()
    assert fake.examined is True
    assert fake.selected is False


def test_first_fetch_reads_tail_and_persists_cursor(tmp_path: Path) -> None:
    store = _store(tmp_path)
    fake = FakeImap(uids=[1, 2, 3], uid_validity=42)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    assert [r["uid"] for r in records] == [1, 2, 3]
    state = store.get("imap-1")
    assert state is not None
    assert state.last_uid == 3
    assert state.uid_validity == 42


def test_uid_polling_delta(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        SyncState(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            last_uid=10,
            uid_validity=42,
            last_synced_at=datetime.now(UTC),
        )
    )
    fake = FakeImap(uids=[8, 9, 10, 11, 12], uid_validity=42)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    # Only UIDs > 10 should be returned.
    assert [r["uid"] for r in records] == [11, 12]
    state = store.get("imap-1")
    assert state is not None
    assert state.last_uid == 12


def test_uidvalidity_change_triggers_resync(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        SyncState(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            last_uid=10,
            uid_validity=42,
            last_synced_at=datetime.now(UTC),
        )
    )
    # New UIDVALIDITY (99) differs from stored (42) → server has been rebuilt.
    fake = FakeImap(uids=[1, 2, 3], uid_validity=99)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    assert [r["uid"] for r in records] == [1, 2, 3]
    state = store.get("imap-1")
    assert state is not None
    assert state.uid_validity == 99


def test_cold_start_returns_tail_50(tmp_path: Path) -> None:
    """Cold start (no prior cursor) is bounded at the last 50 UIDs."""
    store = _store(tmp_path)
    uids = list(range(1, 201))  # 200 messages
    fake = FakeImap(uids=uids, uid_validity=1)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    # Cold-start tail = last 50.
    assert len(records) == 50
    assert [r["uid"] for r in records] == list(range(151, 201))
    state = store.get("imap-1")
    assert state is not None
    assert state.last_uid == 200


def test_fetch_capped_at_100(tmp_path: Path) -> None:
    """Warm fetch capped at 100 even when 150 new UIDs are above watermark."""
    store = _store(tmp_path)
    store.upsert(
        SyncState(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            last_uid=50,
            uid_validity=1,
            last_synced_at=datetime.now(UTC),
        )
    )
    uids = list(range(1, 201))  # 150 above watermark
    fake = FakeImap(uids=uids, uid_validity=1)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    assert len(records) == 100
    # The cap takes the first 100 results (which after sorted is 51..150).
    assert [r["uid"] for r in records] == list(range(51, 151))
    state = store.get("imap-1")
    assert state is not None
    assert state.last_uid == 150


def test_logout_called_in_finally(tmp_path: Path) -> None:
    store = _store(tmp_path)
    fake = FakeImap(uids=[1], uid_validity=1)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    client.fetch_new()
    assert fake.logged_out is True


def test_failure_marks_error_and_reraises(tmp_path: Path) -> None:
    store = _store(tmp_path)

    class Boom(FakeImap):
        def login(self, user: str, password: str) -> tuple[str, list[bytes]]:
            raise RuntimeError("login broke")

    fake = Boom(uids=[], uid_validity=1)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    with pytest.raises(RuntimeError):
        client.fetch_new()
    state = store.get("imap-1")
    assert state is not None
    assert state.last_error == "login broke"


def test_account_id_property(tmp_path: Path) -> None:
    fake = FakeImap(uids=[], uid_validity=1)
    client = ImapHostgatorClient(
        _entry(),
        _store(tmp_path),
        password="pw",
        imap_factory=lambda: fake,
    )
    assert client.account_id == "imap-1"


# ---------------------------------------------------------------------------
# UIDVALIDITY fallback path + logout / fetch edge cases
# ---------------------------------------------------------------------------


class FakeImapStatusFallback(FakeImap):
    """Force the response("UIDVALIDITY") branch to miss so STATUS is used."""

    def response(self, key: str) -> tuple[str, list[bytes] | None]:
        # Return a non-matching status to force the STATUS fallback branch.
        return ("OTHER", None)


def test_uidvalidity_status_fallback(tmp_path: Path) -> None:
    fake = FakeImapStatusFallback(uids=[1, 2], uid_validity=4242)
    client = ImapHostgatorClient(
        _entry(), _store(tmp_path), password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    assert [r["uid"] for r in records] == [1, 2]


class FakeImapBadUidValidity(FakeImap):
    """response() returns a non-numeric token to exercise the parse error path."""

    def response(self, key: str) -> tuple[str, list[bytes] | None]:
        if key == "UIDVALIDITY":
            return ("UIDVALIDITY", [b"not-a-number"])
        return (key, None)


def test_uidvalidity_invalid_response_raises(tmp_path: Path) -> None:
    fake = FakeImapBadUidValidity(uids=[1], uid_validity=1)
    store = _store(tmp_path)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    with pytest.raises(RuntimeError):
        client.fetch_new()
    # mark_error path was exercised.
    state = store.get("imap-1")
    assert state is not None
    assert state.last_error is not None


class FakeImapStatusMissingMarker(FakeImap):
    """STATUS reply lacks UIDVALIDITY token entirely."""

    def response(self, key: str) -> tuple[str, list[bytes] | None]:
        return ("OTHER", None)

    def status(self, mailbox: str, names: str) -> tuple[str, list[bytes]]:
        return ("OK", [b"INBOX (MESSAGES 5)"])


def test_uidvalidity_missing_in_status_raises(tmp_path: Path) -> None:
    fake = FakeImapStatusMissingMarker(uids=[1], uid_validity=1)
    store = _store(tmp_path)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    with pytest.raises(RuntimeError):
        client.fetch_new()


class FakeImapNoFetchPayload(FakeImap):
    """UID FETCH returns no usable bytes payload — _fetch_message returns None."""

    def uid(self, command: str, *args: Any) -> tuple[str, list[Any]]:
        if command == "FETCH":
            # Tuple shape but second element is not bytes — exercises the
            # `return None` branch of _fetch_message.
            return ("OK", [(b"meta", "not-bytes")])
        return super().uid(command, *args)


def test_fetch_message_returns_none_when_no_bytes_payload(tmp_path: Path) -> None:
    fake = FakeImapNoFetchPayload(uids=[1, 2], uid_validity=1)
    store = _store(tmp_path)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    records = client.fetch_new()
    # No usable payloads → no records, but the cursor still advances.
    assert records == []


class FakeImapLogoutBoom(FakeImap):
    def logout(self) -> tuple[str, list[bytes]]:
        raise RuntimeError("logout failed mid-bye")


def test_logout_failure_does_not_invalidate_fetch(tmp_path: Path) -> None:
    fake = FakeImapLogoutBoom(uids=[5, 6], uid_validity=1)
    store = _store(tmp_path)
    client = ImapHostgatorClient(
        _entry(), store, password="pw", imap_factory=lambda: fake
    )
    # Logout failure is logged + swallowed; fetch result is preserved.
    records = client.fetch_new()
    assert [r["uid"] for r in records] == [5, 6]
    state = store.get("imap-1")
    assert state is not None
    assert state.last_uid == 6


def test_parse_uid_search_handles_strings_and_garbage(tmp_path: Path) -> None:
    """Cover the non-bytes / non-int branches of _parse_uid_search."""
    from pf_runtime.communications.clients import imap_hostgator as mod

    # str piece + a token that is not an int + duplicate
    parsed = mod._parse_uid_search(["1 2", b"3 not-a-uid", b"4"])
    assert parsed == [1, 2, 3, 4]
    # Empty inputs short-circuit.
    assert mod._parse_uid_search([]) == []
    assert mod._parse_uid_search([42]) == []  # non bytes/str piece skipped


def test_default_imap_factory_returns_imap4_ssl() -> None:
    """Smoke: the production factory is callable and returns an IMAP4_SSL."""
    import imaplib

    from pf_runtime.communications.clients.imap_hostgator import _default_imap_factory

    # We can't actually connect, but we can verify the function exists and is
    # bound to imaplib.IMAP4_SSL via type. Calling it would attempt a real
    # network connect, so we patch IMAP4_SSL to capture args.
    captured: dict[str, Any] = {}

    class _StubSSL:
        def __init__(self, host: str, port: int) -> None:
            captured["host"] = host
            captured["port"] = port

    real = imaplib.IMAP4_SSL
    imaplib.IMAP4_SSL = _StubSSL  # type: ignore[misc,assignment]
    try:
        _default_imap_factory()
    finally:
        imaplib.IMAP4_SSL = real  # type: ignore[misc]
    assert captured == {"host": "imap.hostgator.com", "port": 993}
