"""Optional PrettyFly OS agent-event writeback (Stage 4 v2).

POSTs to ``PFOS_AGENT_EVENT_URL`` with ``Authorization: Bearer`` when both
URL and ``PFOS_AGENT_EVENT_TOKEN`` are set. If either is missing, all entry
points no-op (reversible kill-switch per integration plan).

Optional: set ``PFOS_AGENT_EVENT_REQUIRE_HTTPS=1`` (or ``true``) to reject
non-``https`` URLs in production.

Optional: set ``PFOS_JOURNAL_EVENT_MIRROR=1`` to mirror each PFOS payload to
stdout as an ``event="agent_event"`` JSON line for the PFOS Phase 4.13
journalctl bridge. Set ``PFOS_JOURNAL_SERVICE`` to the systemd unit/process
name when it differs from the default ``pf-runtime``.

Payload shape matches PFOS ``AgentEventWritePayload`` / ``isAgentEventPayload``.
PFOS accepts ``surface="pf_runtime"`` for runtime-originated events; the
``data.kind="pf_runtime_reply"`` marker keeps reply events filterable inside
the fleet surface.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

_log = logging.getLogger(__name__)

_PFOS_EVENT_URL_ENV_KEY = "PFOS_AGENT_EVENT_URL"
# Name of the env var that holds the bearer token (value is never embedded in code).
_PFOS_EVENT_AUTH_ENV_KEY = "PFOS_AGENT_EVENT_TOKEN"
_PFOS_REQUIRE_HTTPS_ENV_KEY = "PFOS_AGENT_EVENT_REQUIRE_HTTPS"
_PFOS_JOURNAL_MIRROR_ENV_KEY = "PFOS_JOURNAL_EVENT_MIRROR"
_PFOS_JOURNAL_SERVICE_ENV_KEY = "PFOS_JOURNAL_SERVICE"

# Phase 2 communications-triage writeback endpoints. Each emits a separate
# scoped Bearer token so a leak of one cannot forge the other. URL includes
# the silo segment (`/api/silos/<silo>/agent-action`), so callers swap the
# silo segment per-account; the env value is the base URL with a literal
# `<silo>` placeholder that emit_action_sync() / emit_todo_sync() replace.
_PFOS_INBOX_ACTION_URL_ENV_KEY = "PFOS_INBOX_ACTION_URL"
_PFOS_INBOX_ACTION_AUTH_ENV_KEY = "PFOS_INBOX_ACTION_TOKEN"
_PFOS_INBOX_TODO_URL_ENV_KEY = "PFOS_INBOX_TODO_URL"
_PFOS_INBOX_TODO_AUTH_ENV_KEY = "PFOS_INBOX_TODO_TOKEN"


def _env_truthy(key: str) -> bool:
    v = os.environ.get(key, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _url_is_httpish(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("https", "http") and bool(parsed.netloc)


def _url_allowed(url: str) -> bool:
    if not _url_is_httpish(url):
        return False
    if _env_truthy(_PFOS_REQUIRE_HTTPS_ENV_KEY):
        return urlparse(url).scheme == "https"
    return True


def is_configured() -> bool:
    """Return True when emit would attempt HTTP(S) (both env vars non-empty)."""
    url = os.environ.get(_PFOS_EVENT_URL_ENV_KEY, "").strip()
    token = os.environ.get(_PFOS_EVENT_AUTH_ENV_KEY, "").strip()
    return bool(url and token)


def runtime_reply_payload(
    *,
    channel: str,
    profile_slug: str,
    text_preview: str,
    session_id: str | None = None,
    inbound_preview: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Build a ``STATE_CHANGED`` payload for a successful assistant reply."""
    data: dict[str, Any] = {
        "kind": "pf_runtime_reply",
        "channel": channel,
        "text_preview": text_preview[:2000],
    }
    if session_id:
        data["session_id"] = session_id
    if inbound_preview is not None:
        data["inbound_preview"] = inbound_preview[:500]
    out: dict[str, Any] = {
        "type": "STATE_CHANGED",
        "data": data,
        "agent_slug": profile_slug,
        "surface": "pf_runtime",
        "cwd_project": profile_slug,
    }
    if trace_id:
        out["trace_id"] = trace_id
    return out


def runtime_proposal_payload(
    *,
    profile_slug: str,
    skill_slug: str,
    agent_slug: str,
    action_id: str,
    action_type: str,
    account_id: str,
    target_id: str,
    rationale_preview: str,
    confidence_bucket: str | None = None,
    session_id: str | None = None,
    trace_id: str | None = None,
    parent_run_id: str | None = None,
) -> dict[str, Any]:
    """Build an ``ARTIFACT_CREATED`` payload for a communications-triage proposal.

    PFOS Stage 4 v2 fields (``skill_slug``, ``surface``, ``cwd_project``,
    ``parent_run_id``) carry skill-attribution and chain linkage. The
    ``data.kind="pf_runtime_proposal"`` marker keeps proposals filterable
    inside the fleet surface alongside ``pf_runtime_reply`` events.
    """
    data: dict[str, Any] = {
        "kind": "pf_runtime_proposal",
        "action_id": action_id,
        "action_type": action_type,
        "account_id": account_id,
        "target_id": target_id,
        "rationale_preview": rationale_preview[:500],
    }
    if confidence_bucket:
        data["confidence_bucket"] = confidence_bucket
    if session_id:
        data["session_id"] = session_id
    out: dict[str, Any] = {
        "type": "ARTIFACT_CREATED",
        "data": data,
        "surface": "pf_runtime",
        "agent_slug": agent_slug,
        "skill_slug": skill_slug,
        "cwd_project": profile_slug,
        "status": "pending",
    }
    if trace_id:
        out["trace_id"] = trace_id
    if parent_run_id:
        out["parent_run_id"] = parent_run_id
    return out


def _post_json(url: str, token: str, body: dict[str, Any]) -> tuple[int, str]:
    """POST JSON; return (status_code, response_text). status 0 on transport error."""
    payload = json.dumps(body, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310
            raw = resp.read().decode("utf-8", errors="replace")
            return int(resp.status), raw
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", errors="replace")
        except Exception:
            raw = ""
        return int(e.code), raw
    except (urllib.error.URLError, TimeoutError, OSError):
        _log.warning("pfos agent-event request failed", exc_info=True)
        return 0, ""


def _journal_row_from_payload(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    event_type = payload.get("type")
    if not isinstance(event_type, str) or not event_type:
        return None

    data_raw = payload.get("data")
    data = dict(data_raw) if isinstance(data_raw, Mapping) else {}
    status_raw = payload.get("status")
    service = os.environ.get(_PFOS_JOURNAL_SERVICE_ENV_KEY, "pf-runtime").strip()
    if not service:
        service = "pf-runtime"
    agent_slug = payload.get("agent_slug")
    if not isinstance(agent_slug, str) or not agent_slug:
        agent_slug = payload.get("cwd_project")

    row: dict[str, Any] = {
        "event": "agent_event",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "service": service,
        "type": event_type,
        "status": status_raw if isinstance(status_raw, str) and status_raw else "approved",
        "data": data,
    }
    if isinstance(agent_slug, str) and agent_slug:
        row["agent_slug"] = agent_slug
    for key in ("trace_id", "surface", "cwd_project", "skill_slug", "parent_run_id"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            row[key] = value
    return row


def _emit_journal_mirror(payload: Mapping[str, Any]) -> None:
    """Mirror a PFOS payload to stdout as journalctl-readable ground truth."""
    if not _env_truthy(_PFOS_JOURNAL_MIRROR_ENV_KEY):
        return
    try:
        row = _journal_row_from_payload(payload)
        if row is None:
            return
        print(json.dumps(row, separators=(",", ":"), default=str), flush=True)
    except Exception:
        _log.warning("pfos journal mirror failed", exc_info=True)


def emit_agent_event_sync(payload: Mapping[str, Any]) -> bool:
    """POST ``payload`` to PFOS. No-op when not configured. True on HTTP 2xx."""
    payload_dict = dict(payload)
    _emit_journal_mirror(payload_dict)
    if not is_configured():
        return False
    url = os.environ[_PFOS_EVENT_URL_ENV_KEY].strip()
    token = os.environ[_PFOS_EVENT_AUTH_ENV_KEY].strip()
    if not _url_allowed(url):
        if _url_is_httpish(url) and _env_truthy(_PFOS_REQUIRE_HTTPS_ENV_KEY):
            _log.warning("pfos agent-event URL must use https when %s is set", _PFOS_REQUIRE_HTTPS_ENV_KEY)
        else:
            _log.warning("pfos agent-event URL must be http(s) with a host")
        return False
    status, _ = _post_json(url, token, payload_dict)
    if 200 <= status < 300:
        return True
    if status:
        _log.warning("pfos agent-event non-success: status=%s", status)
    return False


async def emit_agent_event(payload: Mapping[str, Any]) -> bool:
    """Async wrapper (thread pool) so callers never block the event loop on I/O."""
    return await asyncio.to_thread(emit_agent_event_sync, dict(payload))


# ---------------------------------------------------------------------------
# Phase 2: inbox-action + agent-todo writeback (per-silo URLs)
# ---------------------------------------------------------------------------


def _format_silo_url(template: str, silo: str) -> str:
    """Insert ``silo`` into a URL template containing ``<silo>``.

    The env value looks like:
        https://os.prettyflyforai.com/api/silos/<silo>/agent-action
    The PFOS server validates the slug against ``WRITEBACK_SLUGS`` so any
    silo bypassing the in-process whitelist (``silo_map.VALID_SILOS``)
    fails fast at the endpoint with HTTP 400 ``invalid_silo``.
    """
    if "<silo>" not in template:
        return template
    return template.replace("<silo>", silo)


_ACTION_TYPE_TO_NAME: dict[str, str] = {
    "reply_draft": "inbox.reply_draft",
    "archive": "inbox.archive",
    "label": "inbox.label",
    "move_folder": "inbox.move_folder",
    "mark_read": "inbox.mark_read",
    "trash": "inbox.trash",
    "unsubscribe_draft": "inbox.unsubscribe_draft",
    "calendar_hold": "calendar.hold",
    "calendar_update": "calendar.update",
    "follow_up_task": "inbox.follow_up_task",
}

_ACTION_TYPE_TO_SIDE_EFFECT: dict[str, str] = {
    "reply_draft": "write",
    "archive": "write",
    "label": "write",
    "move_folder": "write",
    "mark_read": "write",
    "trash": "write",
    "unsubscribe_draft": "external",
    "calendar_hold": "write",
    "calendar_update": "write",
    "follow_up_task": "write",
}


def runtime_action_payload(
    *,
    action_type: str,
    bucket: str,
    account_id: str,
    target_id: str,
    confidence: float,
    rationale: str = "",
    sender: str = "",
    subject: str = "",
    draft_text: str | None = None,
    also_seen_in: tuple[str, ...] | None = None,
    trace_id: str | None = None,
    priority: str | None = None,
    label_suggestion: str | None = None,
    calendar_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the body for ``POST /api/silos/<silo>/agent-action``.

    ``action_type`` is the ``ActionType.value`` slug (``reply_draft``,
    ``archive``, etc.); this helper translates it to the PFOS-side
    ``inbox.*`` / ``calendar.*`` action_name + the right side_effect_class.

    ``also_seen_in`` is the cross-account dedupe trail wired in Phase 3;
    in Phase 2 it's populated with a single-element list ``[account_id]``.

    ``calendar_metadata`` is Phase 5: a dict from
    :func:`pf_runtime.communications.triage_skill._correlate_schedule` with
    one or more of ``proposed_start_iso``, ``meeting_url``, and
    ``freebusy_conflict``. Each key is forwarded verbatim into ``params_json``
    so PFOS renders the SCHEDULE card without a schema change. Pass ``None``
    (the default) for non-SCHEDULE actions.
    """
    action_name = _ACTION_TYPE_TO_NAME.get(action_type, f"inbox.{action_type}")
    side_effect = _ACTION_TYPE_TO_SIDE_EFFECT.get(action_type, "write")
    params: dict[str, Any] = {
        "message_id": target_id,
        "subject": subject[:280],
        "sender": {"name": "", "address": sender},
        "bucket": bucket,
        "confidence": confidence,
        "also_seen_in": list(also_seen_in or (account_id,)),
    }
    if rationale:
        params["rationale_preview"] = rationale[:500]
    if draft_text:
        params["draft_text"] = draft_text[:2000]
    if priority:
        params["priority"] = priority
    if label_suggestion:
        params["label_suggestion"] = label_suggestion
    if calendar_metadata:
        # Forward the keys we recognize so a future field added to the
        # caller's dict doesn't silently leak into params_json.
        for key in ("proposed_start_iso", "meeting_url", "freebusy_conflict"):
            if key in calendar_metadata:
                params[key] = calendar_metadata[key]
    body: dict[str, Any] = {
        "action_name": action_name,
        "side_effect_class": side_effect,
        "params_json": params,
        "confidence": confidence,
        "revert_payload_json": {"original_state": "proposed"},
    }
    if trace_id:
        body["trace_id"] = trace_id
    return body


def runtime_todo_payload(
    *,
    title: str,
    confidence: float,
    est_minutes: int | None = None,
    due_at_iso: str | None = None,
    message_id: str | None = None,
    action_id: str | None = None,
    trace_id: str | None = None,
) -> dict[str, Any]:
    """Build the body for ``POST /api/silos/<silo>/agent-todo``.

    Fired for NEEDS_ALEX_TODAY classifications. ``message_id`` and
    ``action_id`` thread into ``context`` so the PFOS lane can link
    back to the source mail + the paired agent_actions row.
    """
    body: dict[str, Any] = {
        "title": title.strip()[:300],
        "confidence": confidence,
    }
    if est_minutes is not None:
        body["est_minutes"] = est_minutes
    if due_at_iso is not None:
        body["due_at"] = due_at_iso
    ctx: dict[str, Any] = {}
    if message_id:
        ctx["message_id"] = message_id
    if action_id:
        ctx["action_id"] = action_id
    if ctx:
        body["context"] = ctx
    if trace_id:
        body["trace_id"] = trace_id
    return body


def _emit_silo_writeback_sync(
    payload: Mapping[str, Any],
    *,
    silo: str,
    url_env_key: str,
    token_env_key: str,
    kind: str,
) -> bool:
    """POST a writeback payload to a silo-scoped PFOS URL.

    Shared implementation for inbox-action + inbox-todo. Returns True on
    HTTP 2xx, False on missing config / non-2xx / transport error. The
    triage loop treats a False return as a soft failure: the local
    SQLite row stays, the next cycle's emit retries.
    """
    url_template = os.environ.get(url_env_key, "").strip()
    token = os.environ.get(token_env_key, "").strip()
    if not (url_template and token):
        return False
    url = _format_silo_url(url_template, silo)
    if not _url_allowed(url):
        if _url_is_httpish(url) and _env_truthy(_PFOS_REQUIRE_HTTPS_ENV_KEY):
            _log.warning(
                "pfos %s URL must use https when %s is set",
                kind,
                _PFOS_REQUIRE_HTTPS_ENV_KEY,
            )
        else:
            _log.warning("pfos %s URL must be http(s) with a host", kind)
        return False
    status, body = _post_json(url, token, dict(payload))
    if 200 <= status < 300:
        return True
    if status:
        _log.warning(
            "pfos %s non-success: status=%s body=%s", kind, status, body[:200]
        )
    return False


def emit_action_sync(payload: Mapping[str, Any], *, silo: str) -> bool:
    """POST an inbox-action payload to PFOS for ``silo``. No-op when unconfigured."""
    return _emit_silo_writeback_sync(
        payload,
        silo=silo,
        url_env_key=_PFOS_INBOX_ACTION_URL_ENV_KEY,
        token_env_key=_PFOS_INBOX_ACTION_AUTH_ENV_KEY,
        kind="inbox-action",
    )


def emit_todo_sync(payload: Mapping[str, Any], *, silo: str) -> bool:
    """POST an agent-todo payload to PFOS for ``silo``. No-op when unconfigured."""
    return _emit_silo_writeback_sync(
        payload,
        silo=silo,
        url_env_key=_PFOS_INBOX_TODO_URL_ENV_KEY,
        token_env_key=_PFOS_INBOX_TODO_AUTH_ENV_KEY,
        kind="inbox-todo",
    )


async def emit_action(payload: Mapping[str, Any], *, silo: str) -> bool:
    """Async wrapper for emit_action_sync — never blocks the event loop."""
    return await asyncio.to_thread(emit_action_sync, dict(payload), silo=silo)


async def emit_todo(payload: Mapping[str, Any], *, silo: str) -> bool:
    """Async wrapper for emit_todo_sync — never blocks the event loop."""
    return await asyncio.to_thread(emit_todo_sync, dict(payload), silo=silo)
