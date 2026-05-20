"""Agent events emitter — Hermes profile → PFOS agent_events writeback.

Reads a profile's ``config.yaml``, extracts the ``event:`` block declared for
a tool in ``tools.contracts.<tool>.event``, builds an ADR-compliant payload,
and POSTs to PFOS ``/api/silos/<silo>/agent-event``.

Contract source: ``_meta/decisions/2026-05-18-hermes-pfos-event-contract.md``.

Required env:
    HERMES_AGENT_EVENTS_TOKEN  Bearer token (scope ``agent_events:write``)
Optional env:
    HERMES_AGENT_EVENTS_URL    Base URL (defaults to https://os.prettyflyforai.com)

Stdlib-only except PyYAML (already in the Hermes runtime env).
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

import yaml

# Top-level fields the event-contract ADR requires on every row.
REQUIRED_TOP_LEVEL = ("agent_slug", "type", "status", "surface", "cwd_project", "skill_slug")

# Required keys inside ``data``.
REQUIRED_DATA = ("runtime", "private_payload_redacted")

# Default PFOS silo for events not tied to a domain (per WRITEBACK_SLUGS in PFOS).
DEFAULT_SILO_SLUG = "skills"

# Slugs (silo + agent + skill) must match this shape to be safe to interpolate
# into URLs. PFOS enforces the same convention server-side.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class EmitError(RuntimeError):
    """Raised when the emitter cannot ship an ADR-compliant event."""


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _load_profile_config(profile_dir: Path) -> dict[str, Any]:
    cfg_path = profile_dir / "config.yaml"
    if not cfg_path.exists():
        raise EmitError(f"profile config.yaml not found: {cfg_path}")
    with cfg_path.open() as fh:
        return yaml.safe_load(fh) or {}


def _profile_slug(profile_dir: Path, cfg: Mapping[str, Any]) -> str:
    """Profile slug — prefer config.profile, fall back to directory name."""
    return str(cfg.get("profile") or profile_dir.name)


def _event_block(cfg: Mapping[str, Any], tool: str) -> dict[str, Any]:
    """Pull the ``event:`` block for ``tool`` from ``tools.contracts.<tool>``."""
    contracts = (cfg.get("tools") or {}).get("contracts") or {}
    tool_cfg = contracts.get(tool)
    if not tool_cfg:
        raise EmitError(f"tool not declared in config.tools.contracts: {tool}")
    event = tool_cfg.get("event")
    if not event:
        raise EmitError(f"tool {tool!r} has no event: block; cannot emit")
    return dict(event)


def _validate(payload: Mapping[str, Any]) -> None:
    """Assert all ADR-required fields are present and non-empty."""
    missing = [k for k in REQUIRED_TOP_LEVEL if not payload.get(k)]
    if missing:
        raise EmitError(f"payload missing required top-level fields: {missing}")
    data = payload.get("data") or {}
    missing_data = [k for k in REQUIRED_DATA if data.get(k) in (None, "")]
    if missing_data:
        raise EmitError(f"payload.data missing required fields: {missing_data}")


# --------------------------------------------------------------------------- #
# Public surface
# --------------------------------------------------------------------------- #


def build_payload(
    profile_dir: str | Path,
    tool: str,
    overrides: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a contract-compliant payload for ``tool`` declared in profile config.

    Overrides may include top-level fields (``confidence``, ``trace_id``) and a
    nested ``data`` dict whose keys merge into the payload's data block. The
    library refuses to ship a payload missing any ADR-required field.
    """
    profile_dir = Path(profile_dir).expanduser().resolve()
    cfg = _load_profile_config(profile_dir)
    event = _event_block(cfg, tool)

    agent_slug = _profile_slug(profile_dir, cfg)

    payload: dict[str, Any] = {
        "agent_slug": agent_slug,
        "type": event["type"],
        "status": event.get("status", "pending"),
        "surface": event.get("surface", "cli"),
        "cwd_project": event.get("cwd_project") or "fleet",
        "skill_slug": event.get("skill_slug"),  # required — no fallback per the ADR
    }

    data: dict[str, Any] = {
        "schema_version": "hermes.agent_event.v1",
        "runtime": event.get("data_runtime", "hermes"),
        "proposal_status": event.get("data_proposal_status", "proposed"),
        "private_payload_redacted": event.get("private_payload_redacted", True),
    }
    # any config-declared data_* fields (besides the known three) flow into data
    for key, value in event.items():
        if key.startswith("data_") and key not in ("data_runtime", "data_proposal_status"):
            data[key.removeprefix("data_")] = value

    overrides = dict(overrides or {})
    data.update(dict(overrides.pop("data", {}) or {}))
    payload["data"] = data
    payload.update(overrides)

    _validate(payload)
    return payload


def emit_event(
    profile_dir: str | Path,
    tool: str,
    overrides: Mapping[str, Any] | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Build payload + POST to PFOS. Returns the response JSON.

    With ``dry_run=True`` no HTTP call is made; the built payload is returned
    under the ``payload`` key for inspection.
    """
    payload = build_payload(profile_dir, tool, overrides)
    if dry_run:
        return {"dry_run": True, "payload": payload}

    profile_dir = Path(profile_dir).expanduser().resolve()
    cfg = _load_profile_config(profile_dir)
    event = _event_block(cfg, tool)
    silo = event.get("silo_slug") or DEFAULT_SILO_SLUG
    if not _SLUG_RE.match(str(silo)):
        raise EmitError(f"silo_slug must match {_SLUG_RE.pattern!r}: {silo!r}")

    token = (os.environ.get("HERMES_AGENT_EVENTS_TOKEN") or "").strip()
    if not token:
        raise EmitError(
            "HERMES_AGENT_EVENTS_TOKEN not set; source "
            "~/.config/prettyfly-marketing/hermes-tokens.env"
        )
    base = os.environ.get("HERMES_AGENT_EVENTS_URL", "https://os.prettyflyforai.com")
    url = f"{base}/api/silos/{silo}/agent-event"

    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not surface response body — server error pages can echo request
        # context that includes the Authorization header on misconfigured PFOS.
        raise EmitError(f"PFOS rejected event (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise EmitError(f"PFOS unreachable at {url}: {exc.reason}") from exc
