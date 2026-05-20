#!/usr/bin/env python3
"""CLI wrapper around hermes.lib.agent_events.emit_event.

Usage:
    python3 scripts/emit-agent-event.py \\
        --profile cmo \\
        --tool weekly_decision.propose \\
        --readout-path "_inbox/cmo-readouts/2026-05-19-week-of-2026-05-19.md" \\
        --decision continue \\
        --confidence 0.7

The ``--profile`` argument accepts either a profile name (resolved against
``hermes/profiles/``) or an absolute path.

Exit codes:
    0  success — prints the inserted row UUID
    1  emitter error — prints the failure to stderr
    2  argument error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hermes.lib.agent_events import EmitError, emit_event  # noqa: E402


def resolve_profile(arg: str) -> Path:
    """Resolve a ``--profile`` argument to a profile directory."""
    candidate = Path(arg).expanduser()
    if candidate.is_dir():
        return candidate.resolve()
    # Treat as a profile name under hermes/profiles/
    named = ROOT / "hermes" / "profiles" / arg
    if named.is_dir():
        return named.resolve()
    raise FileNotFoundError(f"profile not found: {arg}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit a Hermes → PFOS agent_events row per the profile's contract.",
    )
    parser.add_argument("--profile", required=True, help="Profile name or path")
    parser.add_argument("--tool", required=True, help="Tool name (e.g. weekly_decision.propose)")
    parser.add_argument("--readout-path", help="Vault-relative readout path")
    parser.add_argument("--decision", help="Decision rendered (continue, narrow, pause, ...)")
    parser.add_argument("--confidence", type=float, help="0.0-1.0 confidence")
    parser.add_argument("--trace-id", help="Optional trace identifier")
    parser.add_argument(
        "--extra-json",
        help="Extra fields merged into data block (JSON object string)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print payload without POSTing")
    return parser.parse_args(argv)


def build_overrides(args: argparse.Namespace) -> dict:
    overrides: dict = {}
    data: dict = {}
    if args.readout_path:
        data["readout_path"] = args.readout_path
    if args.decision:
        data["decision"] = args.decision
    if args.extra_json:
        try:
            data.update(json.loads(args.extra_json))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"--extra-json is not valid JSON: {exc}")
    if data:
        overrides["data"] = data
    if args.confidence is not None:
        overrides["confidence"] = args.confidence
    if args.trace_id:
        overrides["trace_id"] = args.trace_id
    return overrides


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        profile_dir = resolve_profile(args.profile)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    overrides = build_overrides(args)

    try:
        result = emit_event(profile_dir, args.tool, overrides, dry_run=args.dry_run)
    except EmitError as exc:
        print(f"emit failed: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(result["payload"], indent=2))
        return 0

    event_id = result.get("event_id")
    if event_id:
        print(event_id)
        return 0
    # unexpected shape but no exception — print whole response for debugging
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
