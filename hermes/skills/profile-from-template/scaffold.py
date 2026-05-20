#!/usr/bin/env python3
"""Scaffold a new Hermes profile from the Atlas-shaped template.

Reads a JSON config file describing a new profile, copies every file under
``_template/`` into ``hermes/profiles/<name>/`` with ``__KEY__`` placeholders
substituted, creates the empty subdirs + AGENTS.md symlink, adds the
rate-cap entry to ``fleet/limits.json``, and runs ``scripts/lint-profile.sh``.

The template ships a rung-1 (read-only) profile with one declared source-read
tool, no propose-write tools, and no event contracts. Promoting a profile to
rung 2 is a deliberate manual step — see the SKILL.md for guidance.

Exit codes:
    0  scaffold succeeded and lint passed
    1  scaffold succeeded but lint surfaced warnings (soft mode) OR scaffold failed
    2  argument / config error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
SKILL_DIR = THIS_FILE.parent
TEMPLATE_DIR = SKILL_DIR / "_template"
REPO_ROOT = SKILL_DIR.parent.parent.parent  # hermes/skills/profile-from-template -> agents/
PROFILES_DIR = REPO_ROOT / "hermes" / "profiles"
LIMITS_PATH = REPO_ROOT / "fleet" / "limits.json"
LINT_SCRIPT = REPO_ROOT / "scripts" / "lint-profile.sh"

REQUIRED_KEYS = (
    "profile_name",
    "description",
    "domain",
    "channels",
    "daily_cap",
    "model_default",
    "model_escalate",
    "source_tool_name",
)

NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{1,30}$")
TOOL_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
CHANNELS_ALLOWED = {"none", "slack_dm", "telegram"}


def _die(msg: str, code: int = 2) -> None:
    print(f"profile-from-template: {msg}", file=sys.stderr)
    sys.exit(code)


def _validate(params: dict) -> None:
    """Reject obvious bad input up front — name, tool shape, channels, cap."""
    missing = [k for k in REQUIRED_KEYS if k not in params]
    if missing:
        _die(f"config missing required keys: {missing}")
    name = params["profile_name"]
    if not NAME_RE.match(name):
        _die(f"profile_name {name!r} must match {NAME_RE.pattern}")
    if not TOOL_RE.match(params["source_tool_name"]):
        _die(f"source_tool_name {params['source_tool_name']!r} must match {TOOL_RE.pattern}")
    if params["channels"] not in CHANNELS_ALLOWED:
        _die(f"channels must be one of {sorted(CHANNELS_ALLOWED)}, got {params['channels']!r}")
    try:
        cap = int(params["daily_cap"])
    except (TypeError, ValueError):
        _die(f"daily_cap must be int, got {params['daily_cap']!r}")
    if cap < 0:
        _die(f"daily_cap must be >= 0, got {cap}")
    params["daily_cap"] = cap


def _substitute(content: str, params: dict) -> str:
    """Replace every ``__KEY__`` with str(params[key]). Unmatched placeholders pass through."""
    for k, v in params.items():
        content = content.replace(f"__{k.upper()}__", str(v))
    return content


def _copy_templates(dest: Path, params: dict) -> int:
    """Walk _template/ recursively, substitute, write. Returns count of files written."""
    if not TEMPLATE_DIR.is_dir():
        _die(f"template dir missing: {TEMPLATE_DIR}")
    count = 0
    for tmpl in TEMPLATE_DIR.rglob("*"):
        if tmpl.is_dir():
            continue
        rel = tmpl.relative_to(TEMPLATE_DIR)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        # Read as bytes so binary-ish placeholder files (none today) survive.
        # Substitute only on UTF-8-decodable text — skip otherwise.
        raw = tmpl.read_bytes()
        try:
            text = raw.decode("utf-8")
            text = _substitute(text, params)
            out.write_text(text, encoding="utf-8")
        except UnicodeDecodeError:
            out.write_bytes(raw)
        count += 1
    return count


def _add_rate_cap(name: str, cap: int) -> bool:
    """Append a rate-cap entry to fleet/limits.json. Returns True if a new entry was written."""
    raw = json.loads(LIMITS_PATH.read_text())
    limits = raw.setdefault("limits", {})
    if name in limits:
        return False
    limits[name] = cap
    LIMITS_PATH.write_text(json.dumps(raw, indent=2) + "\n")
    return True


def _run_lint(name: str) -> bool:
    """Run scripts/lint-profile.sh <name>. Returns True on PASS."""
    if not LINT_SCRIPT.is_file():
        print(f"lint script not found at {LINT_SCRIPT} — skipping lint", file=sys.stderr)
        return True
    result = subprocess.run(
        ["bash", str(LINT_SCRIPT), name],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result.returncode == 0 and "PASS" in result.stdout


def scaffold(config_path: Path) -> int:
    if not config_path.is_file():
        _die(f"config file not found: {config_path}")
    try:
        params = json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        _die(f"config is not valid JSON: {exc}")
    if not isinstance(params, dict):
        _die("config must be a JSON object")
    _validate(params)

    name = params["profile_name"]
    dest = PROFILES_DIR / name
    if dest.exists():
        _die(f"profile already exists at {dest} — refusing to overwrite", code=1)

    print(f"scaffolding {name} at {dest}")
    dest.mkdir(parents=True)

    count = _copy_templates(dest, params)
    print(f"  wrote {count} files from template")

    for sub in ("skills", "eval", "memory"):
        (dest / sub).mkdir(exist_ok=True)
    print("  created empty skills/, eval/, memory/")

    agents_link = dest / "AGENTS.md"
    if not agents_link.exists():
        agents_link.symlink_to("CLAUDE.md")
    print("  created AGENTS.md -> CLAUDE.md symlink")

    added = _add_rate_cap(name, params["daily_cap"])
    print(f"  fleet/limits.json: {'added' if added else 'already had'} {name}={params['daily_cap']}")

    print("running lint:")
    if not _run_lint(name):
        print(f"\nLINT FAILED for {name} — review warnings above before pushing", file=sys.stderr)
        return 1

    print(f"\nscaffold complete for {name}.")
    print(f"  next steps:")
    print(f"    1. fill in {dest}/SOUL.md, DOCTRINE.md, USER.md, MEMORY.md with persona content")
    print(f"    2. add at least one propose-write tool to config.yaml using Marin's weekly_decision.propose as template")
    print(f"    3. cross-link the new event type into CLAUDE.md (lint enforces this)")
    print(f"    4. push to runtime: bash scripts/sync-profile.sh push {name}")
    return 0


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scaffold a new Hermes profile from the Atlas-shaped template.")
    parser.add_argument("--config", required=True, help="Path to JSON config file (see SKILL.md for shape)")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(sys.argv[1:])
    sys.exit(scaffold(Path(args.config).expanduser().resolve()))
