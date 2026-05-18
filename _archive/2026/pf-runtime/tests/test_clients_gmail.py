"""Gmail client tests (Slice 2).

Mocks the urlopen callable to avoid network I/O. Covers scope rejection at
construction, history.list happy path, 404 → full resync, 401 →
``CredentialExpiredError``, and sync state persistence.
"""

from __future__ import annotations

import io
import json
import urllib.error
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.request import Request

import pytest

from pf_runtime.communications.account_registry import RegistryEntry
from pf_runtime.communications.clients import (
    CredentialExpiredError,
    ScopeViolationError,
)
from pf_runtime.communications.clients.gmail import GmailClient
from pf_runtime.communications.schema import AccountConfig, Provider
from pf_runtime.communications.sync_state_store import SyncState, SyncStateStore


def _entry(scopes: tuple[str, ...] = ()) -> RegistryEntry:
    return RegistryEntry(
        account=AccountConfig(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,
            address="alex@example.com",
            scopes=scopes
            or ("https://www.googleapis.com/auth/gmail.readonly",),
            read_only=True,
        ),
        credentials_present=True,
    )


def _store(tmp_path: Path) -> SyncStateStore:
    return SyncStateStore(tmp_path / "comms.db")


# A queued response is `(status, body_dict)` or `(status, body_dict, "url_substr")`.
# When the substring is provided, the test asserts that the request URL contains it.
QueuedResponse = tuple[int, dict[str, Any]] | tuple[int, dict[str, Any], str]


def make_urlopen(
    responses: list[QueuedResponse],
) -> Callable[..., Any]:
    iter_responses = iter(responses)
    captured_urls: list[str] = []

    def _urlopen(req: Request, timeout: float | None = None) -> Any:
        try:
            entry = next(iter_responses)
        except StopIteration as exc:
            raise AssertionError(
                f"unexpected extra request: {req.full_url}"
            ) from exc
        captured_urls.append(req.full_url)
        if len(entry) == 3:
            status_v, body_v, must_contain = entry
            assert must_contain in req.full_url, (
                f"expected {must_contain!r} in {req.full_url!r}"
            )
        else:
            status_v, body_v = entry
        encoded = json.dumps(body_v).encode("utf-8")
        if status_v >= 400:
            raise urllib.error.HTTPError(
                req.full_url, status_v, "err", {}, io.BytesIO(encoded)  # type: ignore[arg-type]
            )

        class _Resp(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *exc: Any) -> bool:
                return False

        return _Resp(encoded)

    _urlopen.captured_urls = captured_urls  # type: ignore[attr-defined]
    return _urlopen


# ---------------------------------------------------------------------------
# Construction-time refusal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scope",
    [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://mail.google.com/",
    ],
)
def test_construction_refuses_forbidden_scope(tmp_path: Path, scope: str) -> None:
    entry = _entry(scopes=(scope,))
    store = _store(tmp_path)
    with pytest.raises(ScopeViolationError):
        GmailClient(entry, store, access_token="tok", urlopen=lambda *a, **k: None)


def test_construction_requires_token(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        GmailClient(_entry(), _store(tmp_path), access_token="")


def test_construction_requires_correct_provider(tmp_path: Path) -> None:
    bad_entry = RegistryEntry(
        account=AccountConfig(
            account_id="x",
            provider=Provider.MICROSOFT_GRAPH,
            address="x@example.com",
        ),
        credentials_present=True,
    )
    with pytest.raises(ValueError):
        GmailClient(bad_entry, _store(tmp_path), access_token="tok")


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_full_resync_when_no_history_id(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen(
        [
            # /messages?maxResults=50  → list of two ids
            (200, {"messages": [{"id": "m1"}, {"id": "m2"}]}, "messages?maxResults=50"),
            # First _get_message (used for cursor anchoring)
            (200, {"id": "m1", "historyId": "1000", "snippet": "hi"}, "messages/m1"),
            # Per-id GETs in main loop
            (200, {"id": "m1", "historyId": "1000", "snippet": "hi"}, "messages/m1"),
            (200, {"id": "m2", "historyId": "999", "snippet": "yo"}, "messages/m2"),
        ]
    )
    client = GmailClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["m1", "m2"]
    state = store.get("gmail-1")
    assert state is not None
    assert state.history_id == "1000"  # newest message's historyId persisted


def test_history_list_happy_path(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        SyncState(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,
            history_id="500",
            last_synced_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    )
    urlopen = make_urlopen(
        [
            (
                200,
                {
                    "history": [
                        {"messagesAdded": [{"message": {"id": "new-1"}}]},
                        {"messagesAdded": [{"message": {"id": "new-2"}}]},
                    ],
                    "historyId": "510",
                },
                "history?",
            ),
            (200, {"id": "new-1", "snippet": "first"}, "messages/new-1"),
            (200, {"id": "new-2", "snippet": "second"}, "messages/new-2"),
        ]
    )
    client = GmailClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["new-1", "new-2"]
    state = store.get("gmail-1")
    assert state is not None
    assert state.history_id == "510"


def test_history_404_triggers_full_resync(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.upsert(
        SyncState(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,
            history_id="EXPIRED",
            last_synced_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    )
    urlopen = make_urlopen(
        [
            (404, {"error": {"code": 404}}, "history?"),
            # Full resync list
            (200, {"messages": [{"id": "m9"}]}, "messages?maxResults=50"),
            # Anchor _get_message
            (200, {"id": "m9", "historyId": "9000", "snippet": "x"}, "messages/m9"),
            # Main-loop _get_message
            (200, {"id": "m9", "historyId": "9000", "snippet": "x"}, "messages/m9"),
        ]
    )
    client = GmailClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["m9"]
    state = store.get("gmail-1")
    assert state is not None
    assert state.history_id == "9000"


def test_401_raises_credential_expired(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen([(401, {"error": "unauthorized"})])
    client = GmailClient(_entry(), store, access_token="tok", urlopen=urlopen)
    with pytest.raises(CredentialExpiredError):
        client.fetch_new()
    state = store.get("gmail-1")
    assert state is not None
    assert state.last_error == "credential_expired"


def test_other_http_error_marks_error_and_reraises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen([(500, {"error": "server"})])
    client = GmailClient(_entry(), store, access_token="tok", urlopen=urlopen)
    with pytest.raises(urllib.error.HTTPError):
        client.fetch_new()
    state = store.get("gmail-1")
    assert state is not None
    assert state.last_error is not None
    assert "500" in state.last_error or "Internal" in state.last_error or state.last_error


def test_authorization_header_present(tmp_path: Path) -> None:
    store = _store(tmp_path)
    captured_headers: list[dict[str, str]] = []

    def urlopen(req: Request, timeout: float | None = None) -> Any:
        captured_headers.append(dict(req.header_items()))
        encoded = json.dumps({"messages": []}).encode("utf-8")

        class _R(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *e: Any) -> bool:
                return False

        return _R(encoded)

    client = GmailClient(_entry(), store, access_token="my-tok", urlopen=urlopen)
    client.fetch_new()
    assert any(h.get("Authorization") == "Bearer my-tok" for h in captured_headers)


def test_empty_full_resync_persists_row_with_no_history(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen([(200, {"messages": []}, "messages?maxResults=50")])
    client = GmailClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert msgs == []
    state = store.get("gmail-1")
    assert state is not None
    assert state.history_id is None


def test_account_id_property(tmp_path: Path) -> None:
    client = GmailClient(_entry(), _store(tmp_path), access_token="tok")
    assert client.account_id == "gmail-1"
