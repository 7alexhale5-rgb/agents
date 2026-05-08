"""Microsoft Graph client tests (Slice 2).

Mocks urlopen to avoid network. Covers scope rejection, deltaLink lifecycle
(cold start → nextLink page → deltaLink persist), 410 → cold-resync, and
429 → retry honoring Retry-After.
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
    FetchError,
    ScopeViolationError,
)
from pf_runtime.communications.clients.graph import GraphClient
from pf_runtime.communications.schema import AccountConfig, Provider
from pf_runtime.communications.sync_state_store import SyncState, SyncStateStore


def _entry(scopes: tuple[str, ...] = ("Mail.Read",)) -> RegistryEntry:
    return RegistryEntry(
        account=AccountConfig(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            address="alex@kohoconsulting.com",
            scopes=scopes,
            read_only=True,
        ),
        credentials_present=True,
    )


def _store(tmp_path: Path) -> SyncStateStore:
    return SyncStateStore(tmp_path / "comms.db")


QueuedResponse = (
    tuple[int, dict[str, Any]]
    | tuple[int, dict[str, Any], dict[str, str]]
    | tuple[int, dict[str, Any], str]
)


def make_urlopen(responses: list[QueuedResponse]) -> Callable[..., Any]:
    iter_responses = iter(responses)
    captured: list[str] = []

    def _urlopen(req: Request, timeout: float | None = None) -> Any:
        try:
            entry = next(iter_responses)
        except StopIteration as exc:
            raise AssertionError(
                f"unexpected extra request: {req.full_url}"
            ) from exc
        captured.append(req.full_url)
        headers: dict[str, str] = {}
        if len(entry) == 3:
            third = entry[2]
            if isinstance(third, dict):
                headers = third
            elif isinstance(third, str):
                assert third in req.full_url, f"expected {third!r} in {req.full_url!r}"
        status_v, body_v = entry[0], entry[1]
        encoded = json.dumps(body_v).encode("utf-8")
        if status_v >= 400:
            err = urllib.error.HTTPError(
                req.full_url, status_v, "err", headers, io.BytesIO(encoded)  # type: ignore[arg-type]
            )
            return _raise(err)

        class _Resp(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *exc: Any) -> bool:
                return False

        return _Resp(encoded)

    _urlopen.captured = captured  # type: ignore[attr-defined]
    return _urlopen


def _raise(exc: BaseException) -> Any:
    raise exc


# ---------------------------------------------------------------------------
# Construction-time refusal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "scope", ["Mail.ReadWrite", "Mail.Send", "Calendars.ReadWrite"]
)
def test_construction_refuses_forbidden_scope(tmp_path: Path, scope: str) -> None:
    store = _store(tmp_path)
    with pytest.raises(ScopeViolationError):
        GraphClient(
            _entry(scopes=(scope,)),
            store,
            access_token="tok",
            urlopen=lambda *a, **k: None,
        )


def test_construction_requires_token(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        GraphClient(_entry(), _store(tmp_path), access_token="")


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
        GraphClient(bad, _store(tmp_path), access_token="tok")


# ---------------------------------------------------------------------------
# Delta lifecycle
# ---------------------------------------------------------------------------


def test_cold_start_with_nextlink_then_deltalink(tmp_path: Path) -> None:
    store = _store(tmp_path)
    next_url = "https://graph.microsoft.com/v1.0/page/2"
    delta_url = "https://graph.microsoft.com/v1.0/me/.../delta?$deltatoken=ABC"
    urlopen = make_urlopen(
        [
            (
                200,
                {
                    "value": [{"id": "m1", "subject": "first"}],
                    "@odata.nextLink": next_url,
                },
                "messages/delta",
            ),
            (
                200,
                {
                    "value": [{"id": "m2", "subject": "second"}],
                    "@odata.deltaLink": delta_url,
                },
                "page/2",
            ),
        ]
    )
    client = GraphClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["m1", "m2"]
    state = store.get("graph-1")
    assert state is not None
    assert state.delta_link == delta_url


def test_warm_start_uses_stored_delta_link(tmp_path: Path) -> None:
    store = _store(tmp_path)
    stored_delta = "https://graph.microsoft.com/v1.0/me/.../delta?$deltatoken=PRIOR"
    new_delta = "https://graph.microsoft.com/v1.0/me/.../delta?$deltatoken=NEXT"
    store.upsert(
        SyncState(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            delta_link=stored_delta,
            last_synced_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    )
    urlopen = make_urlopen(
        [
            (
                200,
                {
                    "value": [{"id": "m3"}],
                    "@odata.deltaLink": new_delta,
                },
                "PRIOR",
            )
        ]
    )
    client = GraphClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["m3"]
    state = store.get("graph-1")
    assert state is not None
    assert state.delta_link == new_delta


def test_410_triggers_cold_resync(tmp_path: Path) -> None:
    store = _store(tmp_path)
    stored_delta = "https://graph.microsoft.com/expired"
    new_delta = "https://graph.microsoft.com/v1.0/me/.../delta?$deltatoken=POST_GONE"
    store.upsert(
        SyncState(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            delta_link=stored_delta,
            last_synced_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
    )
    urlopen = make_urlopen(
        [
            (410, {"error": "Gone"}, "expired"),
            (
                200,
                {
                    "value": [{"id": "m4"}],
                    "@odata.deltaLink": new_delta,
                },
                "messages/delta",
            ),
        ]
    )
    client = GraphClient(_entry(), store, access_token="tok", urlopen=urlopen)
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["m4"]
    state = store.get("graph-1")
    assert state is not None
    assert state.delta_link == new_delta


# ---------------------------------------------------------------------------
# Auth + throttling
# ---------------------------------------------------------------------------


def test_401_raises_credential_expired(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen([(401, {"error": "auth"})])
    client = GraphClient(_entry(), store, access_token="tok", urlopen=urlopen)
    with pytest.raises(CredentialExpiredError):
        client.fetch_new()
    state = store.get("graph-1")
    assert state is not None
    assert state.last_error == "credential_expired"


def test_429_retries_once_with_retry_after(tmp_path: Path) -> None:
    store = _store(tmp_path)
    delta = "https://graph.microsoft.com/v1.0/me/.../delta?$deltatoken=POST_RETRY"
    urlopen = make_urlopen(
        [
            (429, {"error": "throttle"}, {"Retry-After": "2"}),
            (200, {"value": [{"id": "m5"}], "@odata.deltaLink": delta}),
        ]
    )
    sleeps: list[float] = []

    client = GraphClient(
        _entry(),
        store,
        access_token="tok",
        urlopen=urlopen,
        sleep=sleeps.append,
    )
    msgs = client.fetch_new()
    assert [m["id"] for m in msgs] == ["m5"]
    assert sleeps == [2.0]
    state = store.get("graph-1")
    assert state is not None
    assert state.delta_link == delta


def test_second_429_raises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen(
        [
            (429, {"error": "throttle"}, {"Retry-After": "1"}),
            (429, {"error": "throttle again"}, {"Retry-After": "1"}),
        ]
    )
    sleeps: list[float] = []
    client = GraphClient(
        _entry(),
        store,
        access_token="tok",
        urlopen=urlopen,
        sleep=sleeps.append,
    )
    with pytest.raises(FetchError):
        client.fetch_new()
    assert sleeps == [1.0]


def test_429_with_missing_retry_after_defaults_to_one_second(tmp_path: Path) -> None:
    store = _store(tmp_path)
    delta = "https://graph.microsoft.com/v1.0/me/.../delta?$deltatoken=NO_RA"
    urlopen = make_urlopen(
        [
            (429, {"error": "throttle"}),
            (200, {"value": [], "@odata.deltaLink": delta}),
        ]
    )
    sleeps: list[float] = []
    client = GraphClient(
        _entry(),
        store,
        access_token="tok",
        urlopen=urlopen,
        sleep=sleeps.append,
    )
    client.fetch_new()
    assert sleeps == [1.0]


def test_authorization_header_present(tmp_path: Path) -> None:
    store = _store(tmp_path)
    captured: list[dict[str, str]] = []

    def urlopen(req: Request, timeout: float | None = None) -> Any:
        captured.append(dict(req.header_items()))
        body = json.dumps({"value": [], "@odata.deltaLink": "https://x"}).encode("utf-8")

        class _R(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *e: Any) -> bool:
                return False

        return _R(body)

    client = GraphClient(_entry(), store, access_token="g-tok", urlopen=urlopen)
    client.fetch_new()
    assert any(h.get("Authorization") == "Bearer g-tok" for h in captured)


def test_other_http_error_marks_error_and_reraises(tmp_path: Path) -> None:
    store = _store(tmp_path)
    urlopen = make_urlopen([(500, {"error": "boom"})])
    client = GraphClient(_entry(), store, access_token="tok", urlopen=urlopen)
    with pytest.raises(urllib.error.HTTPError):
        client.fetch_new()
    state = store.get("graph-1")
    assert state is not None
    assert state.last_error
