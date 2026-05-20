"""Draft-only Gmail adapter for Marin.

This module is intentionally separate from shared-skills/email-triage, which
remains read-only. The only sanctioned operation here is creating an unsent
Gmail draft through users.drafts.create, then emitting a redacted PFOS event.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol

from hermes.lib.agent_events import emit_event

_GMAIL_DRAFT_TOOL = "marin.gmail_create_draft"
_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]


class GmailDraftError(RuntimeError):
    """Raised when the draft-only adapter cannot create a Gmail draft."""


class _Executable(Protocol):
    def execute(self) -> dict[str, Any]: ...


class _DraftsResource(Protocol):
    def create(self, *, userId: str, body: dict[str, Any]) -> _Executable: ...


class _UsersResource(Protocol):
    def drafts(self) -> _DraftsResource: ...


class _GmailService(Protocol):
    def users(self) -> _UsersResource: ...


def _hash_identifier(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _raw_message(*, to: str, subject: str, body_text: str, body_html: str | None = None) -> str:
    to = to.strip()
    subject = subject.strip()
    if not to:
        raise ValueError("to is required")
    if not subject:
        raise ValueError("subject is required")
    if not body_text and not body_html:
        raise ValueError("body_text or body_html is required")

    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject

    if body_html:
        message.set_content(body_text or "")
        message.add_alternative(body_html, subtype="html")
    else:
        message.set_content(body_text)

    return base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")


def _token_path() -> Path:
    override = os.environ.get("HERMES_GOOGLE_TOKEN_PATH")
    if override:
        return Path(override).expanduser()
    home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return home / "google_token.json"


def _stored_token_scopes(token_path: Path) -> list[str]:
    try:
        payload = json.loads(token_path.read_text())
    except Exception:
        return list(_SCOPES)
    scopes = payload.get("scopes")
    if isinstance(scopes, list) and scopes:
        return [str(scope) for scope in scopes]
    return list(_SCOPES)


def _build_gmail_service() -> _GmailService:
    token_path = _token_path()
    if not token_path.exists():
        raise GmailDraftError(f"Google token not found: {token_path}")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GmailDraftError(
            "Google API client packages are unavailable; install Hermes Google Workspace support"
        ) from exc

    creds = Credentials.from_authorized_user_file(str(token_path), _stored_token_scopes(token_path))
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        payload = json.loads(creds.to_json())
        payload.setdefault("type", "authorized_user")
        token_path.write_text(json.dumps(payload, indent=2))
        token_path.chmod(0o600)
    if not creds.valid:
        raise GmailDraftError("Google token is invalid; rerun Google Workspace setup")

    return build("gmail", "v1", credentials=creds)


def create_draft(
    profile_dir: str | Path,
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    target_account: str | None = None,
    service: _GmailService | None = None,
    dry_run_event: bool = False,
) -> dict[str, Any]:
    """Create one Gmail draft and emit one redacted Marin event.

    Returns raw Gmail identifiers plus hashed recipient/account metadata.
    The event contains no subject, body, raw recipient, or raw account.
    """
    raw = _raw_message(to=to, subject=subject, body_text=body_text, body_html=body_html)
    gmail = service or _build_gmail_service()
    try:
        response = gmail.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw}},
        ).execute()
    except Exception as exc:  # pragma: no cover - exercised by live runtime
        raise GmailDraftError("Gmail draft creation failed") from exc

    message = response.get("message") or {}
    result = {
        "draft_id": response.get("id"),
        "message_id": message.get("id"),
        "thread_id": message.get("threadId"),
        "recipient_hash": _hash_identifier(to),
        "target_account_hash": _hash_identifier(target_account),
    }

    emission = emit_event(
        profile_dir,
        _GMAIL_DRAFT_TOOL,
        overrides={
            "data": {
                "draft_id": result["draft_id"],
                "message_id": result["message_id"],
                "thread_id": result["thread_id"],
                "recipient_hash": result["recipient_hash"],
                "target_account_hash": result["target_account_hash"],
                "gmail_endpoint": "users.drafts.create",
            }
        },
        dry_run=dry_run_event,
    )
    return {"draft": result, "event": emission}
