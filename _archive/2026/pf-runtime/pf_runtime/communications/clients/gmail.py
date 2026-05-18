"""Sync, stdlib-only Gmail client for communications triage v1.

Polls ``users.history.list`` to discover new ``messageAdded`` events, falls
back to a bounded ``users.messages.list`` resync when the stored history-id
expires (HTTP 404), and fetches each new message via
``users.messages.get?format=full``. Only the read-only Gmail scope is
acceptable — construction refuses any write/modify/send/full-access scope.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
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

_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"
_FULL_RESYNC_LIMIT = 50
_FORBIDDEN_GMAIL_SCOPES: frozenset[str] = frozenset(
    {
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://mail.google.com/",
    }
)


class GmailClient:
    """Read-only Gmail incremental fetcher."""

    def __init__(
        self,
        entry: RegistryEntry,
        sync_store: SyncStateStore,
        *,
        access_token: str,
        urlopen: UrlopenCallable | None = None,
    ) -> None:
        if entry.account.provider is not Provider.GOOGLE_MAIL:
            raise ValueError(
                f"GmailClient requires provider=google_mail; got {entry.account.provider}"
            )
        violating = [s for s in entry.account.scopes if s in _FORBIDDEN_GMAIL_SCOPES]
        if violating:
            raise ScopeViolationError(
                f"GmailClient refuses construction for account "
                f"{entry.account.account_id}: forbidden v1 scope(s) {violating}"
            )
        if not access_token:
            raise ValueError("GmailClient requires a non-empty access_token")
        self._entry = entry
        self._store = sync_store
        self._token = access_token
        self._urlopen: UrlopenCallable = urlopen or _default_urlopen

    @property
    def account_id(self) -> str:
        return self._entry.account.account_id

    def fetch_new(self) -> list[dict[str, Any]]:
        """Return raw message dicts (``users.messages.get`` shape)."""
        log.info(
            "PFRT_GMAIL_FETCH_START account=%s",
            self.account_id,
        )
        try:
            return self._fetch_new_inner()
        except CredentialExpiredError:
            self._store.mark_error(self.account_id, Provider.GOOGLE_MAIL, "credential_expired")
            raise
        except Exception as exc:
            # Mark + re-raise: caller handles the actual error path; we just
            # ensure the cursor row records why this account stopped syncing.
            self._store.mark_error(self.account_id, Provider.GOOGLE_MAIL, str(exc))
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_new_inner(self) -> list[dict[str, Any]]:
        state = self._store.get(self.account_id)
        new_message_ids: list[str]
        new_history_id: str | None
        if state is None or state.history_id is None:
            new_message_ids, new_history_id = self._full_resync()
        else:
            try:
                new_message_ids, new_history_id = self._history_list(state.history_id)
            except _HistoryIdExpired:
                log.info(
                    "PFRT_GMAIL_HISTORY_ID_EXPIRED account=%s prior=%s",
                    self.account_id,
                    state.history_id,
                )
                new_message_ids, new_history_id = self._full_resync()

        messages: list[dict[str, Any]] = []
        for msg_id in new_message_ids:
            msg = self._get_message(msg_id)
            if msg is not None:
                messages.append(msg)

        # Persist the freshest history-id we observed; `_full_resync` returns
        # None when the resync produced no messages, in which case we keep
        # whatever the prior state had (or store a fresh row with no cursor).
        prior_history_id = state.history_id if state is not None else None
        history_id_to_store = new_history_id or prior_history_id
        self._store.upsert(
            SyncState(
                account_id=self.account_id,
                provider=Provider.GOOGLE_MAIL,
                history_id=history_id_to_store,
                last_synced_at=datetime.now(UTC),
            )
        )
        return messages

    def _full_resync(self) -> tuple[list[str], str | None]:
        url = f"{_API_BASE}/messages?maxResults={_FULL_RESYNC_LIMIT}"
        body = self._http_get_json(url)
        msgs_raw = body.get("messages")
        msgs = msgs_raw if isinstance(msgs_raw, list) else []
        ids: list[str] = []
        for entry in msgs:
            if isinstance(entry, dict) and entry.get("id"):
                ids.append(str(entry["id"]))
        # Anchor the cursor to the newest message's historyId so subsequent
        # history.list calls have a starting point. We get this from the
        # first detail fetch in _get_message via the response's `historyId`
        # field — captured below in _fetch_new_inner.
        history_id = self._derive_history_id_from_messages(ids)
        return ids, history_id

    def _derive_history_id_from_messages(self, ids: list[str]) -> str | None:
        # Peek at the newest message (Gmail returns most-recent first) for its
        # historyId. We do a single extra GET; subsequent _get_message calls
        # in the caller will re-fetch but that's fine — the API is idempotent
        # and the first id is typically already in our cache by the time the
        # caller reaches it. To stay simple we just return None when the
        # listing was empty; cursor will be set on the first non-empty pull.
        if not ids:
            return None
        msg = self._get_message(ids[0])
        if msg is None:
            return None
        history_id = msg.get("historyId")
        return str(history_id) if history_id else None

    def _history_list(self, start_history_id: str) -> tuple[list[str], str | None]:
        params = {
            "startHistoryId": start_history_id,
            "historyTypes": "messageAdded",
        }
        url = f"{_API_BASE}/history?{urllib.parse.urlencode(params)}"
        try:
            body = self._http_get_json(url)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise _HistoryIdExpired() from exc
            raise

        new_ids: list[str] = []
        history_raw = body.get("history")
        history = history_raw if isinstance(history_raw, list) else []
        for record in history:
            if not isinstance(record, dict):
                continue
            added_raw = record.get("messagesAdded")
            added = added_raw if isinstance(added_raw, list) else []
            for added_entry in added:
                if not isinstance(added_entry, dict):
                    continue
                msg = added_entry.get("message")
                if isinstance(msg, dict) and msg.get("id"):
                    new_ids.append(str(msg["id"]))

        next_history_id = body.get("historyId")
        return new_ids, str(next_history_id) if next_history_id else None

    def _get_message(self, message_id: str) -> dict[str, Any] | None:
        safe_id = urllib.parse.quote(message_id, safe="")
        url = f"{_API_BASE}/messages/{safe_id}?format=full"
        body = self._http_get_json(url)
        return body if body else None

    def _http_get_json(self, url: str) -> dict[str, Any]:
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
                    f"gmail account {self.account_id}: 401 unauthorized"
                ) from exc
            raise
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise FetchError(f"gmail returned non-JSON body: {exc}") from exc
        if not isinstance(parsed, dict):
            raise FetchError(f"gmail returned non-object body: {type(parsed).__name__}")
        return parsed


class _HistoryIdExpired(Exception):
    """Internal signal: stored history-id was rejected with HTTP 404."""


def _default_urlopen(req: Request, timeout: float | None = None) -> Any:
    # Controlled HTTPS only — S310 ignored repo-wide for this module via
    # pyproject [tool.ruff.lint.per-file-ignores]; bandit nosec for parity.
    return urllib.request.urlopen(req, timeout=timeout)  # nosec B310
