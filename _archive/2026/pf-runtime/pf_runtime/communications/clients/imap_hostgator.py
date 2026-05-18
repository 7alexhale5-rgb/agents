"""Sync, stdlib-only HostGator IMAP client for communications triage v1.

Connects via :class:`imaplib.IMAP4_SSL` on port 993 (the only transport the
manifest allows in v1). Uses ``EXAMINE`` (not ``SELECT``) so messages stay
unread server-side. Tracks the last seen UID + UIDVALIDITY in the sync
state store; a UIDVALIDITY change forces a bounded resync of the most
recent messages.

Construction refuses any port/SSL combination other than 993/SSL and any
``smtp_enabled_v1=true`` setting — the manifest's only allowed transport
is ``imap_ssl_993``.
"""

from __future__ import annotations

import email
import logging
from datetime import UTC, datetime
from email.message import Message as EmailMessage
from typing import Any

from pf_runtime.communications.account_registry import RegistryEntry
from pf_runtime.communications.clients import (
    ImapFactory,
    RegistryValidationError,
)
from pf_runtime.communications.schema import Provider
from pf_runtime.communications.sync_state_store import SyncState, SyncStateStore

log = logging.getLogger(__name__)

_FETCH_CAP = 100
_RESYNC_TAIL = 50


class ImapHostgatorClient:
    """Read-only IMAP fetcher for the v1 HostGator transport."""

    def __init__(
        self,
        entry: RegistryEntry,
        sync_store: SyncStateStore,
        *,
        password: str,
        imap_factory: ImapFactory | None = None,
    ) -> None:
        if entry.account.provider is not Provider.IMAP_HOSTGATOR:
            raise ValueError(
                f"ImapHostgatorClient requires provider=imap_hostgator; "
                f"got {entry.account.provider}"
            )
        if entry.imap is None:
            raise RegistryValidationError(
                f"account {entry.account.account_id}: IMAP entry missing imap settings"
            )
        if entry.imap.port != 993 or entry.imap.ssl is not True:
            raise RegistryValidationError(
                f"account {entry.account.account_id}: IMAP transport must be port=993 ssl=true; "
                f"got port={entry.imap.port} ssl={entry.imap.ssl}"
            )
        if entry.imap.smtp_enabled_v1 is not False:
            raise RegistryValidationError(
                f"account {entry.account.account_id}: smtp_enabled_v1 must be false in v1"
            )
        if not password:
            raise ValueError("ImapHostgatorClient requires a non-empty password")

        self._entry = entry
        self._store = sync_store
        self._password = password
        self._imap_factory: ImapFactory = imap_factory or _default_imap_factory

    @property
    def account_id(self) -> str:
        return self._entry.account.account_id

    def fetch_new(self) -> list[dict[str, Any]]:
        """Return a list of ``{"uid": int, "message": EmailMessage}`` records.

        Matches the shape :func:`providers.normalize_imap_message` accepts via
        its ``uid=`` keyword.
        """
        log.info(
            "PFRT_IMAP_FETCH_START account=%s",
            self.account_id,
        )
        try:
            return self._fetch_new_inner()
        except Exception as exc:
            # Mark + re-raise: caller handles the actual error path; we just
            # ensure the cursor row records why this account stopped syncing.
            self._store.mark_error(self.account_id, Provider.IMAP_HOSTGATOR, str(exc))
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_new_inner(self) -> list[dict[str, Any]]:
        state = self._store.get(self.account_id)
        client = self._imap_factory()
        try:
            client.login(self._entry.account.address, self._password)
            # EXAMINE = read-only SELECT; never sets the \Seen flag.
            examine_status, examine_data = client.examine("INBOX")
            _ensure_ok(examine_status, "EXAMINE INBOX", examine_data)

            server_uid_validity = self._fetch_uidvalidity(client)
            stored_validity = state.uid_validity if state is not None else None
            full_resync = (
                stored_validity is not None and stored_validity != server_uid_validity
            )
            if full_resync:
                log.info(
                    "PFRT_IMAP_UIDVALIDITY_CHANGED account=%s prior=%s server=%s",
                    self.account_id,
                    stored_validity,
                    server_uid_validity,
                )

            uids = self._search_uids(
                client,
                state=state,
                server_uid_validity=server_uid_validity,
                full_resync=full_resync,
            )
            uids = uids[:_FETCH_CAP]

            records: list[dict[str, Any]] = []
            highest_uid = state.last_uid if (state is not None and not full_resync) else None
            for uid in uids:
                msg = self._fetch_message(client, uid)
                if msg is None:
                    continue
                records.append({"uid": uid, "message": msg})
                if highest_uid is None or uid > highest_uid:
                    highest_uid = uid

            self._store.upsert(
                SyncState(
                    account_id=self.account_id,
                    provider=Provider.IMAP_HOSTGATOR,
                    last_uid=highest_uid,
                    uid_validity=server_uid_validity,
                    last_synced_at=datetime.now(UTC),
                )
            )
            return records
        finally:
            try:
                client.logout()
            except Exception:
                # Logout is best-effort; failure here doesn't invalidate the
                # successful fetch above.
                log.warning(
                    "imap account=%s: logout failed", self.account_id, exc_info=True
                )

    def _fetch_uidvalidity(self, client: Any) -> int:
        status, data = client.response("UIDVALIDITY")
        if status == "UIDVALIDITY" and data:
            value = data[0]
            if isinstance(value, bytes | bytearray):
                value = value.decode("ascii", errors="replace")
            try:
                return int(str(value).strip())
            except (TypeError, ValueError) as exc:
                raise RuntimeError(
                    f"imap account {self.account_id}: invalid UIDVALIDITY response {data!r}"
                ) from exc
        # Some IMAP server responses carry the value differently; fall back
        # to STATUS.
        status, data = client.status("INBOX", "(UIDVALIDITY)")
        _ensure_ok(status, "STATUS UIDVALIDITY", data)
        token = b" ".join(d for d in data if isinstance(d, bytes | bytearray))
        text = token.decode("ascii", errors="replace")
        marker = "UIDVALIDITY"
        idx = text.find(marker)
        if idx < 0:
            raise RuntimeError(
                f"imap account {self.account_id}: UIDVALIDITY missing in {text!r}"
            )
        rest = text[idx + len(marker) :].strip().lstrip("(").strip()
        token_str = rest.split()[0].rstrip(")")
        return int(token_str)

    def _search_uids(
        self,
        client: Any,
        *,
        state: SyncState | None,
        server_uid_validity: int,
        full_resync: bool,
    ) -> list[int]:
        if (
            state is None
            or state.last_uid is None
            or full_resync
            or state.uid_validity is None
        ):
            status, data = client.uid("SEARCH", None, "ALL")
            _ensure_ok(status, "UID SEARCH ALL", data)
            uids = _parse_uid_search(data)
            return uids[-_RESYNC_TAIL:]
        next_uid = state.last_uid + 1
        status, data = client.uid("SEARCH", None, f"UID {next_uid}:*")
        _ensure_ok(status, "UID SEARCH range", data)
        uids = _parse_uid_search(data)
        # ``UID SEARCH UID N:*`` returns the highest UID even if < N when no
        # higher messages exist; filter those out so we do not re-process.
        return [u for u in uids if u >= next_uid]

    def _fetch_message(self, client: Any, uid: int) -> EmailMessage | None:
        status, data = client.uid("FETCH", str(uid), "(RFC822)")
        _ensure_ok(status, f"UID FETCH {uid}", data)
        for chunk in data:
            if isinstance(chunk, tuple) and len(chunk) >= 2:
                payload = chunk[1]
                if isinstance(payload, bytes | bytearray):
                    return email.message_from_bytes(bytes(payload))
        return None


def _ensure_ok(status: str, label: str, data: Any) -> None:
    if status != "OK":
        raise RuntimeError(f"imap {label} failed: status={status!r} data={data!r}")


def _parse_uid_search(data: Any) -> list[int]:
    if not data:
        return []
    chunks: list[bytes] = []
    for piece in data:
        if isinstance(piece, bytes | bytearray):
            chunks.append(bytes(piece))
        elif isinstance(piece, str):
            chunks.append(piece.encode("ascii", errors="replace"))
    if not chunks:
        return []
    text = b" ".join(chunks).decode("ascii", errors="replace")
    out: list[int] = []
    for token in text.split():
        try:
            out.append(int(token))
        except ValueError:
            continue
    return sorted(out)


def _default_imap_factory() -> Any:
    import imaplib

    return imaplib.IMAP4_SSL("imap.hostgator.com", 993)
