"""GoogleCalendarClient tests (Phase 5).

Minimal freebusy.query wrapper used by the SCHEDULE-bucket triage branch.
Tests use the same mocked urlopen pattern as the Gmail/Graph clients.
"""

from __future__ import annotations

import io
import json
import urllib.error
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.request import Request

import pytest

from pf_runtime.communications.account_registry import RegistryEntry
from pf_runtime.communications.clients import CredentialExpiredError
from pf_runtime.communications.clients.google_calendar import GoogleCalendarClient
from pf_runtime.communications.schema import AccountConfig, Provider


def _entry(scopes: tuple[str, ...] = ()) -> RegistryEntry:
    return RegistryEntry(
        account=AccountConfig(
            account_id="gmail-1-calendar",
            provider=Provider.GOOGLE_CALENDAR,
            address="alex@example.com",
            scopes=scopes
            or ("https://www.googleapis.com/auth/calendar.readonly",),
            read_only=True,
        ),
        credentials_present=True,
    )


def _make_urlopen(
    responses: list[tuple[int, dict[str, Any]]],
) -> Callable[..., Any]:
    iter_responses = iter(responses)
    captured: list[tuple[str, bytes]] = []

    def _urlopen(req: Request, timeout: float | None = None) -> Any:
        try:
            status, body = next(iter_responses)
        except StopIteration as exc:
            raise AssertionError(
                f"unexpected request: {req.full_url}"
            ) from exc
        captured.append((req.full_url, req.data or b""))
        encoded = json.dumps(body).encode("utf-8")
        if status >= 400:
            raise urllib.error.HTTPError(
                req.full_url, status, "err", {}, io.BytesIO(encoded)  # type: ignore[arg-type]
            )

        class _R(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *e: Any) -> bool:
                return False

        return _R(encoded)

    _urlopen.captured = captured  # type: ignore[attr-defined]
    return _urlopen


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_construction_requires_token() -> None:
    with pytest.raises(ValueError, match="non-empty access_token"):
        GoogleCalendarClient(_entry(), access_token="")


def test_construction_requires_correct_provider() -> None:
    bad_entry = RegistryEntry(
        account=AccountConfig(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,  # wrong
            address="alex@example.com",
            scopes=("https://www.googleapis.com/auth/calendar.readonly",),
            read_only=True,
        ),
        credentials_present=True,
    )
    with pytest.raises(ValueError, match="google_calendar"):
        GoogleCalendarClient(bad_entry, access_token="tok")


@pytest.mark.parametrize(
    "scope",
    [
        "https://www.googleapis.com/auth/calendar",  # full read-write
        "https://www.googleapis.com/auth/calendar.events",  # event write
    ],
)
def test_construction_refuses_write_scopes(scope: str) -> None:
    from pf_runtime.communications.clients import ScopeViolationError

    with pytest.raises(ScopeViolationError, match="forbidden v1 scope"):
        GoogleCalendarClient(
            _entry(scopes=(scope,)),
            access_token="tok",
        )


# ---------------------------------------------------------------------------
# freebusy()
# ---------------------------------------------------------------------------


def test_freebusy_empty_calendar_returns_empty_list() -> None:
    urlopen = _make_urlopen(
        [
            (
                200,
                {
                    "calendars": {
                        "primary": {"busy": []}
                    }
                },
            )
        ]
    )
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    busy = client.freebusy(
        datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
        datetime(2026, 5, 12, 16, 0, tzinfo=UTC),
    )
    assert busy == []


def test_freebusy_single_busy_interval() -> None:
    urlopen = _make_urlopen(
        [
            (
                200,
                {
                    "calendars": {
                        "primary": {
                            "busy": [
                                {
                                    "start": "2026-05-12T14:00:00Z",
                                    "end": "2026-05-12T15:00:00Z",
                                }
                            ]
                        }
                    }
                },
            )
        ]
    )
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    busy = client.freebusy(
        datetime(2026, 5, 12, 13, 0, tzinfo=UTC),
        datetime(2026, 5, 12, 16, 0, tzinfo=UTC),
    )
    assert len(busy) == 1
    start, end = busy[0]
    assert start == datetime(2026, 5, 12, 14, 0, tzinfo=UTC)
    assert end == datetime(2026, 5, 12, 15, 0, tzinfo=UTC)


def test_freebusy_request_body_shape() -> None:
    """POST body must carry timeMin/timeMax in ISO-8601 + items=[primary]."""
    urlopen = _make_urlopen(
        [(200, {"calendars": {"primary": {"busy": []}}})]
    )
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    client.freebusy(
        datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
        datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
    )
    _url, body = urlopen.captured[0]  # type: ignore[attr-defined]
    payload = json.loads(body.decode("utf-8"))
    assert payload["timeMin"] == "2026-05-12T14:00:00+00:00"
    assert payload["timeMax"] == "2026-05-12T15:00:00+00:00"
    assert payload["items"] == [{"id": "primary"}]


def test_freebusy_401_raises_credential_expired() -> None:
    urlopen = _make_urlopen([(401, {"error": "unauthorized"})])
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    with pytest.raises(CredentialExpiredError):
        client.freebusy(
            datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
            datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
        )


def test_freebusy_non_401_wraps_as_fetch_error() -> None:
    """Non-auth HTTP errors (429, 5xx, etc.) wrap as FetchError so callers
    catching FetchError-shaped failures don't see a raw urllib leak."""
    from pf_runtime.communications.clients import FetchError

    urlopen = _make_urlopen([(429, {"error": "rate limited"})])
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    with pytest.raises(FetchError, match="HTTP 429"):
        client.freebusy(
            datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
            datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
        )


def test_freebusy_drops_inverted_intervals() -> None:
    """Defense: if the API returns an interval where end <= start, skip it
    rather than letting it flow into downstream overlap math."""
    urlopen = _make_urlopen(
        [
            (
                200,
                {
                    "calendars": {
                        "primary": {
                            "busy": [
                                # Inverted: end before start
                                {
                                    "start": "2026-05-12T16:00:00Z",
                                    "end": "2026-05-12T15:00:00Z",
                                },
                                # Zero-length: end == start
                                {
                                    "start": "2026-05-12T17:00:00Z",
                                    "end": "2026-05-12T17:00:00Z",
                                },
                                # Valid
                                {
                                    "start": "2026-05-12T18:00:00Z",
                                    "end": "2026-05-12T19:00:00Z",
                                },
                            ]
                        }
                    }
                },
            )
        ]
    )
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    busy = client.freebusy(
        datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
        datetime(2026, 5, 12, 20, 0, tzinfo=UTC),
    )
    # Only the valid 18:00→19:00 interval survives.
    assert len(busy) == 1
    assert busy[0][0] == datetime(2026, 5, 12, 18, 0, tzinfo=UTC)


def test_freebusy_naive_datetime_rejected() -> None:
    urlopen = _make_urlopen([])
    client = GoogleCalendarClient(_entry(), access_token="tok", urlopen=urlopen)
    with pytest.raises(ValueError, match="timezone-aware"):
        client.freebusy(
            datetime(2026, 5, 12, 14, 0),  # naive
            datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
        )


def test_authorization_header_bearer() -> None:
    captured_headers: list[dict[str, str]] = []

    def urlopen(req: Request, timeout: float | None = None) -> Any:
        captured_headers.append(dict(req.header_items()))
        encoded = json.dumps({"calendars": {"primary": {"busy": []}}}).encode("utf-8")

        class _R(io.BytesIO):
            def __enter__(self) -> Any:
                return self

            def __exit__(self, *e: Any) -> bool:
                return False

        return _R(encoded)

    client = GoogleCalendarClient(
        _entry(), access_token="my-cal-token", urlopen=urlopen
    )
    client.freebusy(
        datetime(2026, 5, 12, 14, 0, tzinfo=UTC),
        datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
    )
    assert any(
        h.get("Authorization") == "Bearer my-cal-token" for h in captured_headers
    )


def test_account_id_property() -> None:
    client = GoogleCalendarClient(_entry(), access_token="tok")
    assert client.account_id == "gmail-1-calendar"
