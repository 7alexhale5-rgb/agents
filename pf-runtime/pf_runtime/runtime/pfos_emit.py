"""Optional PrettyFly OS agent-event writeback (Stage 4 v2).

POSTs to ``PFOS_AGENT_EVENT_URL`` with ``Authorization: Bearer`` when both
URL and ``PFOS_AGENT_EVENT_TOKEN`` are set. If either is missing, all entry
points no-op (reversible kill-switch per integration plan).

Optional: set ``PFOS_AGENT_EVENT_REQUIRE_HTTPS=1`` (or ``true``) to reject
non-``https`` URLs in production.

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
from typing import Any
from urllib.parse import urlparse

_log = logging.getLogger(__name__)

_PFOS_EVENT_URL_ENV_KEY = "PFOS_AGENT_EVENT_URL"
# Name of the env var that holds the bearer token (value is never embedded in code).
_PFOS_EVENT_AUTH_ENV_KEY = "PFOS_AGENT_EVENT_TOKEN"
_PFOS_REQUIRE_HTTPS_ENV_KEY = "PFOS_AGENT_EVENT_REQUIRE_HTTPS"


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


def emit_agent_event_sync(payload: Mapping[str, Any]) -> bool:
    """POST ``payload`` to PFOS. No-op when not configured. True on HTTP 2xx."""
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
    status, _ = _post_json(url, token, dict(payload))
    if 200 <= status < 300:
        return True
    if status:
        _log.warning("pfos agent-event non-success: status=%s", status)
    return False


async def emit_agent_event(payload: Mapping[str, Any]) -> bool:
    """Async wrapper (thread pool) so callers never block the event loop on I/O."""
    return await asyncio.to_thread(emit_agent_event_sync, dict(payload))
