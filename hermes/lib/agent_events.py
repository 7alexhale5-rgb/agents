"""Agent events emitter — Hermes profile → PFOS agent_events writeback.

Reads a profile's ``config.yaml``, extracts the ``event:`` block declared for
a tool in ``tools.contracts.<tool>.event``, builds an ADR-compliant payload,
and POSTs to PFOS ``/api/silos/<silo>/agent-event``.

Contract source: ``_meta/decisions/2026-05-18-hermes-pfos-event-contract.md``.

Required env:
    HERMES_AGENT_EVENTS_TOKEN  Bearer token (scope ``agent_events:write``)
Optional env:
    HERMES_AGENT_EVENTS_URL    Base URL (defaults to https://os.prettyflyforai.com)
    HERMES_FLEET_LIMITS_FILE   Path to per-profile daily caps JSON (default: <repo>/fleet/limits.json)
    HERMES_FLEET_COUNTER_FILE  Path to the daily counter store (default: $HERMES_HOME/.emit-counters.json)
    HERMES_HOME                Runtime root for counter state (default: ~/.hermes)

Stdlib-only except PyYAML (already in the Hermes runtime env).
"""

from __future__ import annotations

import datetime as _dt
import fcntl
import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

import yaml

logger = logging.getLogger(__name__)

# Top-level fields the event-contract ADR requires on every row.
REQUIRED_TOP_LEVEL = ("agent_slug", "type", "status", "surface", "cwd_project", "skill_slug")

# Required keys inside ``data``.
REQUIRED_DATA = ("runtime", "private_payload_redacted")

# Default PFOS silo for events not tied to a domain (per WRITEBACK_SLUGS in PFOS).
DEFAULT_SILO_SLUG = "skills"

# Slugs (silo + agent + skill) must match this shape to be safe to interpolate
# into URLs. PFOS enforces the same convention server-side.
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

# Default fleet limits path, resolved relative to the repo root (this file lives
# at hermes/lib/ inside the agents repo). Override via HERMES_FLEET_LIMITS_FILE.
_DEFAULT_LIMITS_PATH = Path(__file__).resolve().parents[2] / "fleet" / "limits.json"


class EmitError(RuntimeError):
    """Raised when the emitter cannot ship an ADR-compliant event."""


class RateLimitExceeded(EmitError):
    """Raised when a profile has hit its daily emit cap.

    Carries structured fields so the calling skill can decide whether to
    queue the proposal locally instead of firing. Caught skills should
    handle this distinctly from generic EmitError (network failure, ADR
    violation) — a rate-limit fire is normal back-pressure, not a bug.
    """

    def __init__(self, profile: str, limit: int, today: str) -> None:
        super().__init__(
            f"rate limit exceeded for profile {profile!r}: "
            f"{limit} emissions already shipped on {today}"
        )
        self.profile = profile
        self.limit = limit
        self.today = today


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
# Rate caps
# --------------------------------------------------------------------------- #


def _limits_path() -> Path:
    override = os.environ.get("HERMES_FLEET_LIMITS_FILE")
    return Path(override).expanduser() if override else _DEFAULT_LIMITS_PATH


def _counter_path() -> Path:
    override = os.environ.get("HERMES_FLEET_COUNTER_FILE")
    if override:
        return Path(override).expanduser()
    home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return home / ".emit-counters.json"


def _load_limits() -> dict[str, int]:
    """Return ``{profile_slug: daily_cap}``. Missing/unreadable file → empty (no caps)."""
    path = _limits_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("fleet limits unreadable at %s (%s) — running uncapped", path, exc)
        return {}
    limits = raw.get("limits") if isinstance(raw, Mapping) else None
    if not isinstance(limits, Mapping):
        return {}
    # Coerce to int and drop non-positive entries (a 0/-1 cap would never let
    # the profile emit; treat that as a config bug → log + skip).
    out: dict[str, int] = {}
    for slug, value in limits.items():
        try:
            n = int(value)
        except (TypeError, ValueError):
            logger.warning("fleet limits: non-int cap for %s (%r) — ignored", slug, value)
            continue
        if n <= 0:
            logger.warning("fleet limits: non-positive cap for %s (%d) — ignored", slug, n)
            continue
        out[str(slug)] = n
    return out


def _today_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")


def _check_and_increment(profile_slug: str) -> None:
    """Enforce the daily cap for ``profile_slug``. No-op if profile is uncapped.

    Uses an fcntl exclusive lock on the counter file to make concurrent
    emit_event calls from cron jobs safe. Old days are pruned on each touch
    so the counter file stays bounded.

    Raises:
        RateLimitExceeded: when the profile is at or above its configured cap.
    """
    limits = _load_limits()
    cap = limits.get(profile_slug)
    if cap is None:
        return  # uncapped — skip the disk write entirely

    today = _today_utc()
    path = _counter_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    # Touch-create with empty JSON so the lock has something to grab on first run.
    if not path.exists():
        path.write_text("{}")

    # r+ to lock + read + write under the same fd. Atomic-rename isn't safe
    # here because we'd lose the lock between read and write — fcntl on the
    # original fd is the simpler correct pattern.
    with path.open("r+") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            raw = fh.read() or "{}"
            try:
                state = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("counter file corrupt at %s — resetting", path)
                state = {}
            if not isinstance(state, dict):
                state = {}

            # Prune any day that isn't today (caps are daily; history is
            # not needed for this enforcement and bloats the file).
            day_bucket = state.get(today)
            if not isinstance(day_bucket, dict):
                day_bucket = {}
            state = {today: day_bucket}

            current = int(day_bucket.get(profile_slug, 0))
            if current >= cap:
                raise RateLimitExceeded(profile_slug, cap, today)

            day_bucket[profile_slug] = current + 1
            state[today] = day_bucket

            fh.seek(0)
            fh.truncate()
            fh.write(json.dumps(state, sort_keys=True, indent=2))
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


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

    # Cap enforcement runs AFTER payload is built (so configuration bugs surface
    # before quota bookkeeping) but BEFORE the POST (so a cap-trip never bills
    # PFOS for a row that won't write). dry_run intentionally bypasses this so
    # callers can inspect built payloads without consuming quota.
    _check_and_increment(str(payload["agent_slug"]))

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
