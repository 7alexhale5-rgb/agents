"""Sync, stdlib-only Google Calendar freebusy client for Phase 5.

Implements just the slice of Calendar v3 the SCHEDULE-bucket triage path
needs — :meth:`GoogleCalendarClient.freebusy` posts to ``/calendar/v3/freeBusy``
and returns the busy intervals on the operator's primary calendar.

This is intentionally minimal:

* No event list, no insert, no patch — V1 policy forbids those.
* Construction refuses any non-readonly Calendar OAuth scope as
  defense-in-depth (same pattern as :class:`GraphClient`).
* The bearer token is passed in by the caller, so the same
  ``RefreshableGoogleCredentials.get_access_token()`` flow used by
  :mod:`pf_runtime.communications.clients.gmail` works here too.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any
from urllib.request import Request

from pf_runtime.communications.account_registry import RegistryEntry
from pf_runtime.communications.clients import (
    CredentialExpiredError,
    FetchError,
    ScopeViolationError,
    UrlopenCallable,
)
from pf_runtime.communications.schema import Provider

log = logging.getLogger(__name__)

_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"

# Scopes that exceed the read-only contract Phase 5 needs. The operator may
# have granted them at provision time — we refuse to use them so a triage
# bug can't accidentally mutate the calendar.
_FORBIDDEN_CALENDAR_SCOPES: frozenset[str] = frozenset(
    {
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    }
)


class GoogleCalendarClient:
    """Read-only Google Calendar freebusy fetcher."""

    def __init__(
        self,
        entry: RegistryEntry,
        *,
        access_token: str,
        urlopen: UrlopenCallable | None = None,
    ) -> None:
        if entry.account.provider is not Provider.GOOGLE_CALENDAR:
            raise ValueError(
                f"GoogleCalendarClient requires provider=google_calendar; "
                f"got {entry.account.provider}"
            )
        violating = [
            s for s in entry.account.scopes if s in _FORBIDDEN_CALENDAR_SCOPES
        ]
        if violating:
            raise ScopeViolationError(
                f"GoogleCalendarClient refuses construction for account "
                f"{entry.account.account_id}: forbidden v1 scope(s) {violating}"
            )
        if not access_token:
            raise ValueError(
                "GoogleCalendarClient requires a non-empty access_token"
            )
        self._entry = entry
        self._token = access_token
        self._urlopen: UrlopenCallable = urlopen or _default_urlopen

    @property
    def account_id(self) -> str:
        return self._entry.account.account_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def freebusy(
        self, time_min: datetime, time_max: datetime
    ) -> list[tuple[datetime, datetime]]:
        """Return busy intervals on the operator's primary calendar.

        Args:
            time_min: Start of the query window (timezone-aware).
            time_max: End of the query window (timezone-aware).

        Returns:
            List of ``(start, end)`` tuples for each busy interval the API
            reports between ``time_min`` and ``time_max``. Empty list when
            the calendar is free across the entire window.

        Raises:
            ValueError: ``time_min`` or ``time_max`` is naive.
            CredentialExpiredError: 401 from the API — caller should refresh
                the token and retry.
            FetchError: Malformed response body.
        """
        if time_min.tzinfo is None or time_max.tzinfo is None:
            raise ValueError(
                "freebusy() requires timezone-aware datetimes for time_min/time_max"
            )
        payload = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "items": [{"id": "primary"}],
        }
        body = self._http_post_json(_FREEBUSY_URL, payload)
        calendars = body.get("calendars")
        if not isinstance(calendars, dict):
            return []
        primary = calendars.get("primary")
        if not isinstance(primary, dict):
            return []
        busy_raw = primary.get("busy")
        busy = busy_raw if isinstance(busy_raw, list) else []
        intervals: list[tuple[datetime, datetime]] = []
        for entry in busy:
            if not isinstance(entry, dict):
                continue
            start_raw = entry.get("start")
            end_raw = entry.get("end")
            if not isinstance(start_raw, str) or not isinstance(end_raw, str):
                continue
            try:
                start = _parse_rfc3339(start_raw)
                end = _parse_rfc3339(end_raw)
            except ValueError:
                continue
            # Drop degenerate / inverted intervals — guards against malformed
            # API responses producing negative-duration overlaps downstream.
            if end <= start:
                continue
            intervals.append((start, end))
        return intervals

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _http_post_json(
        self, url: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with self._urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise CredentialExpiredError(
                    f"google_calendar account {self.account_id}: 401 unauthorized"
                ) from exc
            # Wrap everything else as FetchError so callers see the same
            # abstraction the Gmail/Graph clients expose — a stdlib
            # urllib.error.HTTPError leaking through would surprise callers
            # that catch FetchError-shaped failures.
            raise FetchError(
                f"google_calendar account {self.account_id}: "
                f"HTTP {exc.code}: {exc.reason}"
            ) from exc
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FetchError(
                f"google_calendar returned non-JSON body: {exc}"
            ) from exc
        if not isinstance(parsed, dict):
            raise FetchError(
                f"google_calendar returned non-object body: {type(parsed).__name__}"
            )
        return parsed


def _parse_rfc3339(value: str) -> datetime:
    """Parse an RFC 3339 / ISO 8601 datetime string from the Calendar API."""
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    return datetime.fromisoformat(candidate)


def _default_urlopen(req: Request, timeout: float | None = None) -> Any:
    # Controlled HTTPS only — fixed Calendar API host. S310 ignored per-file
    # via pyproject [tool.ruff.lint.per-file-ignores]; bandit nosec for parity.
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310
