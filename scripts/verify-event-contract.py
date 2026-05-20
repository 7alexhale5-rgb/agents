#!/usr/bin/env python3
"""Verify ``agent_events`` rows against profile-declared event contracts.

Each Hermes profile declares an ``event:`` block per tool in its
``config.yaml`` (see ``_meta/decisions/2026-05-18-hermes-pfos-event-contract.md``).
This verifier compares actual ``agent_events`` rows against those declarations
and reports violations.

Data acquisition is the caller's responsibility — pipe rows in as JSON:

    # From a pre-fetched JSON file
    python3 scripts/verify-event-contract.py --events /tmp/events.json --profile cmo

    # From PFOS in one shot (run from a PFOS-linked dir)
    cd ~/Projects/prettyfly-os && \\
      printf '%s' "SELECT id::text, type, status, surface, cwd_project, skill_slug, data, created_at::text FROM public.agent_events WHERE type LIKE 'cmo.%' ORDER BY created_at DESC LIMIT 50;" \\
      | supabase db query --linked > /tmp/events.json && \\
      python3 ~/Projects/agents/scripts/verify-event-contract.py --events /tmp/events.json --profile cmo

Keeping the SQL out of this script means the verifier is pure logic, free of
shell-out dependencies and free of any SQL-injection surface.

Exit codes:
    0  all rows compliant
    1  one or more violations
    2  argument / config error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "hermes" / "profiles"

# Single source of truth — pull the required-fields lists from the lib so the
# verifier and the emitter cannot drift.
sys.path.insert(0, str(ROOT))
from hermes.lib.agent_events import REQUIRED_DATA, REQUIRED_TOP_LEVEL  # noqa: E402


# --------------------------------------------------------------------------- #
# Loading event declarations from profile configs
# --------------------------------------------------------------------------- #


def load_event_declarations(profile_dirs: Iterable[Path]) -> dict[str, dict[str, Any]]:
    """Return a map ``event.type`` → expected event block for every profile."""
    decls: dict[str, dict[str, Any]] = {}
    for profile_dir in profile_dirs:
        cfg_path = profile_dir / "config.yaml"
        if not cfg_path.exists():
            continue
        with cfg_path.open() as fh:
            cfg = yaml.safe_load(fh) or {}
        contracts = (cfg.get("tools") or {}).get("contracts") or {}
        for tool_cfg in contracts.values():
            event = tool_cfg.get("event") if isinstance(tool_cfg, dict) else None
            if not event or "type" not in event:
                continue
            decl = dict(event)
            decl["_profile"] = profile_dir.name
            decls[event["type"]] = decl
    return decls


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #


def verify_rows(
    rows: list[dict[str, Any]],
    profile_dirs: Iterable[Path],
) -> list[dict[str, str]]:
    """Compare each row against the declaration for its ``type``.

    Rows whose type isn't declared by any profile are skipped (not our contract).
    Returns a list of violations, each shaped:
        {row_id, type, field, expected, actual}
    """
    decls = load_event_declarations(list(profile_dirs))
    violations: list[dict[str, str]] = []

    for row in rows:
        type_ = row.get("type")
        if not type_ or type_ not in decls:
            continue
        decl = decls[type_]

        # Top-level required fields (REQUIRED_TOP_LEVEL imported from the lib).
        # `agent_slug` is in the list but PFOS resolves it server-side from the
        # row's agent_id FK, so we skip the column check for that one field —
        # if the row exists, the agent existed at insert time.
        for field in (f for f in REQUIRED_TOP_LEVEL if f != "agent_slug"):
            actual = row.get(field)
            if actual in (None, ""):
                violations.append({
                    "row_id": str(row.get("id", "<unknown>")),
                    "type": type_,
                    "field": field,
                    "expected": str(decl.get(field, "<non-empty>")),
                    "actual": "NULL",
                })
                continue
            expected = decl.get(field)
            if expected is not None and actual != expected:
                violations.append({
                    "row_id": str(row.get("id", "<unknown>")),
                    "type": type_,
                    "field": field,
                    "expected": str(expected),
                    "actual": str(actual),
                })

        # Data block required fields (REQUIRED_DATA imported from the lib).
        data = row.get("data") or {}
        for field in REQUIRED_DATA:
            actual = data.get(field)
            if actual in (None, ""):
                violations.append({
                    "row_id": str(row.get("id", "<unknown>")),
                    "type": type_,
                    "field": f"data.{field}",
                    "expected": str(decl.get(f"data_{field}", "<non-empty>")),
                    "actual": "NULL",
                })

        # private_payload_redacted must be exactly True (boolean)
        redacted = data.get("private_payload_redacted")
        if redacted is False:
            violations.append({
                "row_id": str(row.get("id", "<unknown>")),
                "type": type_,
                "field": "data.private_payload_redacted",
                "expected": "True",
                "actual": "False",
            })

    return violations


# --------------------------------------------------------------------------- #
# JSON loading — handles either a pure JSON file or supabase CLI output
# (which wraps JSON in pre/post prose like "Initialising login role..." and
# the "A new version..." footer).
# --------------------------------------------------------------------------- #


def _load_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start == -1 or end <= start:
            raise
        parsed = json.loads(text[start:end])
    if isinstance(parsed, dict) and "rows" in parsed:
        return parsed["rows"]
    if isinstance(parsed, list):
        return parsed
    raise ValueError(f"expected list or {{rows: [...]}}, got {type(parsed).__name__}")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify agent_events rows against profile-declared event contracts.",
    )
    parser.add_argument("--events", type=Path, required=True, help="JSON file of pre-fetched events")
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        help="Limit to a specific profile (repeatable). Defaults to all profiles.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.profile:
        profile_dirs = [PROFILES_DIR / name for name in args.profile]
        for path in profile_dirs:
            if not path.is_dir():
                print(f"error: profile not found: {path}", file=sys.stderr)
                return 2
    else:
        profile_dirs = [p for p in PROFILES_DIR.iterdir() if p.is_dir() and not p.name.startswith("_")]

    if not args.events.exists():
        print(f"error: events file not found: {args.events}", file=sys.stderr)
        return 2
    rows = _load_rows(args.events)

    violations = verify_rows(rows, profile_dirs)

    if not violations:
        print(f"verify-event-contract: clean ({len(rows)} rows checked)")
        return 0

    print(f"verify-event-contract: {len(violations)} violation(s):", file=sys.stderr)
    for v in violations:
        print(
            f"  row {v['row_id']} (type={v['type']}): {v['field']} "
            f"expected={v['expected']}, actual={v['actual']}",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
