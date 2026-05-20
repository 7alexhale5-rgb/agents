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
import time
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Protocol

from hermes.lib.agent_events import emit_event

_GMAIL_DRAFT_TOOL = "marin.gmail_create_draft"
_SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_EXPIRY_MARGIN_SECONDS = 60


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


def _profile_dir() -> Path:
    override = os.environ.get("HERMES_GOOGLE_PROFILE_DIR")
    if override:
        return Path(override).expanduser()
    home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return home / "profiles" / "personal"


def _gmail_account_id() -> str:
    return os.environ.get("HERMES_GMAIL_ACCOUNT_ID", "gmail-1")


def _stored_token_scopes(token_path: Path) -> list[str]:
    try:
        payload = json.loads(token_path.read_text())
    except Exception:
        return list(_SCOPES)
    scopes = payload.get("scopes")
    if isinstance(scopes, list) and scopes:
        return [str(scope) for scope in scopes]
    return list(_SCOPES)


def _profile_env_values(profile_dir: Path) -> dict[str, str]:
    path = profile_dir / ".env"
    if not path.exists():
        raise GmailDraftError(f"Google profile env not found: {path}")
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _access_token_from_profile_env() -> str:
    profile_dir = _profile_dir()
    account_id = _gmail_account_id()
    cache_path = profile_dir / "oauth-cache" / f"{account_id}.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text())
        except json.JSONDecodeError:
            cached = {}
        if cached.get("access_token") and cached.get("expires_at", 0) > time.time() + _EXPIRY_MARGIN_SECONDS:
            return str(cached["access_token"])

    env = _profile_env_values(profile_dir)
    refresh_key = "PF_GMAIL_REFRESH_TOKEN_" + account_id.upper().replace("-", "_")
    missing = [
        key
        for key in ("PF_GOOGLE_OAUTH_CLIENT_ID", "PF_GOOGLE_OAUTH_CLIENT_SECRET", refresh_key)
        if not env.get(key)
    ]
    if missing:
        raise GmailDraftError(f"missing Google profile env vars: {', '.join(missing)}")

    body = urllib.parse.urlencode(
        {
            "client_id": env["PF_GOOGLE_OAUTH_CLIENT_ID"],
            "client_secret": env["PF_GOOGLE_OAUTH_CLIENT_SECRET"],
            "refresh_token": env[refresh_key],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        _TOKEN_URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise GmailDraftError("Google token refresh failed") from exc
    access_token = payload.get("access_token")
    if not access_token:
        raise GmailDraftError("Google token refresh returned no access token")

    record = {
        "access_token": access_token,
        "expires_at": time.time() + int(payload.get("expires_in", 3600)),
        "refreshed_at": time.time(),
    }
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(record, indent=2))
    cache_path.chmod(0o600)
    return str(access_token)


def _build_gmail_service() -> _GmailService:
    token_path = _token_path()
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GmailDraftError(
            "Google API client packages are unavailable; install Hermes Google Workspace support"
        ) from exc

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), _stored_token_scopes(token_path))
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            payload = json.loads(creds.to_json())
            payload.setdefault("type", "authorized_user")
            token_path.write_text(json.dumps(payload, indent=2))
            token_path.chmod(0o600)
        if not creds.valid:
            raise GmailDraftError("Google token is invalid; rerun Google Workspace setup")
    else:
        creds = Credentials(token=_access_token_from_profile_env(), scopes=_SCOPES)

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
