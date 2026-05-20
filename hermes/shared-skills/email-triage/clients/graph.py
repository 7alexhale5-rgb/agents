"""Sync, stdlib-only Microsoft Graph client for communications triage v1.

Implements the ``/me/mailFolders/Inbox/messages/delta`` cursor pattern:
* Cold start: GET the delta endpoint with the documented ``$select`` set.
* Warm: GET the stored ``@odata.deltaLink`` URL.
* Page through ``@odata.nextLink`` until ``@odata.deltaLink`` arrives.
* On HTTP 410 Gone: clear the cursor, log, and retry once from cold.
* On HTTP 429: respect ``Retry-After``, sleep, retry once; raise on the
  second 429.

Construction refuses any ``Mail.ReadWrite`` / ``Mail.Send`` /
``Calendars.ReadWrite`` scope as defense-in-depth.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
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
from pf_runtime.communications.sync_state_store import SyncState, SyncStateStore

log = logging.getLogger(__name__)

_DELTA_SELECT = (
    "id,subject,from,toRecipients,ccRecipients,bccRecipients,"
    "receivedDateTime,bodyPreview,hasAttachments"
)
_COLD_START_URL = (
    "https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages/delta"
    f"?$select={_DELTA_SELECT}"
)
_FORBIDDEN_GRAPH_SCOPES: frozenset[str] = frozenset(
    {"Mail.ReadWrite", "Mail.Send", "Calendars.ReadWrite"}
)


class GraphClient:
    """Read-only Microsoft Graph mail-delta fetcher."""

    def __init__(
        self,
        entry: RegistryEntry,
        sync_store: SyncStateStore,
        *,
        access_token: str,
        urlopen: UrlopenCallable | None = None,
        sleep: Any = None,
    ) -> None:
        if entry.account.provider is not Provider.MICROSOFT_GRAPH:
            raise ValueError(
                f"GraphClient requires provider=microsoft_graph; got {entry.account.provider}"
            )
        violating = [s for s in entry.account.scopes if s in _FORBIDDEN_GRAPH_SCOPES]
        if violating:
            raise ScopeViolationError(
                f"GraphClient refuses construction for account "
                f"{entry.account.account_id}: forbidden v1 scope(s) {violating}"
            )
        if not access_token:
            raise ValueError("GraphClient requires a non-empty access_token")
        self._entry = entry
        self._store = sync_store
        self._token = access_token
        self._urlopen: UrlopenCallable = urlopen or _default_urlopen
        self._sleep = sleep if sleep is not None else time.sleep

    @property
    def account_id(self) -> str:
        return self._entry.account.account_id

    def fetch_new(self) -> list[dict[str, Any]]:
        """Return raw Graph message dicts (one per ``@odata.delta`` page entry)."""
        log.info(
            "PFRT_GRAPH_FETCH_START account=%s",
            self.account_id,
        )
        try:
            return self._fetch_new_inner()
        except CredentialExpiredError:
            self._store.mark_error(
                self.account_id, Provider.MICROSOFT_GRAPH, "credential_expired"
            )
            raise
        except Exception as exc:
            # Mark + re-raise: caller handles the actual error path; we just
            # ensure the cursor row records why this account stopped syncing.
            self._store.mark_error(self.account_id, Provider.MICROSOFT_GRAPH, str(exc))
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_new_inner(self) -> list[dict[str, Any]]:
        state = self._store.get(self.account_id)
        start_url = state.delta_link if state is not None and state.delta_link else _COLD_START_URL

        try:
            messages, new_delta_link = self._page(start_url)
        except _DeltaLinkGone:
            log.info("PFRT_GRAPH_DELTA_GONE account=%s", self.account_id)
            messages, new_delta_link = self._page(_COLD_START_URL)

        self._store.upsert(
            SyncState(
                account_id=self.account_id,
                provider=Provider.MICROSOFT_GRAPH,
                delta_link=new_delta_link,
                last_synced_at=datetime.now(UTC),
            )
        )
        return messages

    def _page(self, start_url: str) -> tuple[list[dict[str, Any]], str | None]:
        messages: list[dict[str, Any]] = []
        next_url: str | None = start_url
        delta_link: str | None = None
        while next_url:
            body = self._http_get_json(next_url)
            value = body.get("value")
            if isinstance(value, list):
                messages.extend(v for v in value if isinstance(v, dict))
            next_url = (
                str(body["@odata.nextLink"]) if body.get("@odata.nextLink") else None
            )
            if body.get("@odata.deltaLink"):
                delta_link = str(body["@odata.deltaLink"])
                # deltaLink terminates the page chain by contract.
                break
        return messages, delta_link

    def _http_get_json(self, url: str, *, retry_429: bool = True) -> dict[str, Any]:
        req = Request(
            url,
            method="GET",
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
        )
        try:
            with self._urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            if exc.code == 401:
                raise CredentialExpiredError(
                    f"graph account {self.account_id}: 401 unauthorized"
                ) from exc
            if exc.code == 410:
                raise _DeltaLinkGone() from exc
            if exc.code == 429:
                if not retry_429:
                    raise FetchError(
                        f"graph account {self.account_id}: repeated 429 throttling"
                    ) from exc
                retry_after = self._retry_after_seconds(exc)
                self._sleep(retry_after)
                return self._http_get_json(url, retry_429=False)
            raise
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FetchError(f"graph returned non-JSON body: {exc}") from exc
        if not isinstance(parsed, dict):
            raise FetchError(f"graph returned non-object body: {type(parsed).__name__}")
        return parsed

    @staticmethod
    def _retry_after_seconds(exc: urllib.error.HTTPError) -> float:
        # Headers may be a Message or a plain dict-like.
        header_val: str | None = None
        try:
            header_val = exc.headers.get("Retry-After")
        except AttributeError:
            header_val = None
        if not header_val:
            return 1.0
        try:
            return float(header_val)
        except ValueError:
            return 1.0


class _DeltaLinkGone(Exception):
    """Internal signal: stored deltaLink was rejected with HTTP 410."""


def _default_urlopen(req: Request, timeout: float | None = None) -> Any:
    # Controlled HTTPS only — S310 ignored repo-wide for this module via
    # pyproject [tool.ruff.lint.per-file-ignores]; bandit nosec for parity.
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310
