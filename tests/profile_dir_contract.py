#!/usr/bin/env python3
"""Profile-dir contract test — Phase 4.7 pre-work item B.

Asserts that every profile dir under `~/Projects/agents/hermes/profiles/{slug}/`
is loadable by both:
  1. Hermes' profile loader (validate-profile.sh — already exists)
  2. PF Runtime's profile loader contract (per pf-runtime/SPEC.md)

Failing this test means a profile drift would silently break the runtime swap
at Phase 4.7 cutover. Runs nightly via launchd.

Usage:
    python3 tests/profile_dir_contract.py [--strict]

Exit codes:
    0 — all profiles pass both contracts
    1 — at least one profile fails Hermes contract
    2 — at least one profile fails PF Runtime contract
    3 — at least one profile fails both
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

PROFILES_ROOT = Path.home() / "Projects" / "agents" / "hermes" / "profiles"
VALIDATE_SCRIPT = Path.home() / "Projects" / "agents" / "scripts" / "validate-profile.sh"

# Profile slugs are kebab-case ASCII per filesystem protocol; reject anything
# else before passing to subprocess. Defends against accidental shell-meta /
# path-traversal characters reaching `validate-profile.sh`.
PROFILE_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

# PF Runtime SPEC.md required files + dirs (per `pf-runtime/SPEC.md`)
PF_REQUIRED_FILES = {
    "SOUL.md",
    "USER.md",
    "MEMORY.md",
    "CLAUDE.md",
    "manifest.json",
    "config.yaml",
    "a2a-card.json",
    "pricing.yaml",
}
PF_REQUIRED_DIRS = {
    "rooms",
    "skills",
    "memory",
    "eval",
}
# Optional but expected
PF_OPTIONAL_FILES = {"env.example", "changelog.md"}


def list_profiles() -> list[Path]:
    if not PROFILES_ROOT.is_dir():
        print(f"[FAIL] profiles root missing: {PROFILES_ROOT}", file=sys.stderr)
        sys.exit(1)
    return sorted([p for p in PROFILES_ROOT.iterdir() if p.is_dir() and not p.name.startswith(".")])


def hermes_contract(profile: Path) -> tuple[bool, str]:
    """Run validate-profile.sh against the profile."""
    if not VALIDATE_SCRIPT.is_file():
        return False, f"validate-profile.sh missing at {VALIDATE_SCRIPT}"
    if not PROFILE_SLUG_RE.match(profile.name):
        return False, f"profile name failed slug validation: {profile.name!r}"
    try:
        result = subprocess.run(
            [str(VALIDATE_SCRIPT), profile.name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, "ok"
        return False, result.stdout.strip() + " " + result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)


def pf_contract(profile: Path) -> tuple[bool, list[str]]:
    """Check PF Runtime SPEC.md required files + dirs + JSON validity."""
    failures: list[str] = []

    for fname in PF_REQUIRED_FILES:
        f = profile / fname
        if not f.is_file():
            failures.append(f"missing file: {fname}")

    for dname in PF_REQUIRED_DIRS:
        d = profile / dname
        if not d.is_dir():
            failures.append(f"missing dir: {dname}/")

    # JSON shape checks
    manifest_path = profile / "manifest.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text())
            for key in ("tier",):
                if key not in manifest:
                    failures.append(f"manifest.json missing key: {key}")
        except json.JSONDecodeError as e:
            failures.append(f"manifest.json invalid JSON: {e}")

    a2a_path = profile / "a2a-card.json"
    if a2a_path.is_file():
        try:
            json.loads(a2a_path.read_text())
        except json.JSONDecodeError as e:
            failures.append(f"a2a-card.json invalid JSON: {e}")

    return (len(failures) == 0, failures)


def main() -> int:
    profiles = list_profiles()
    if not profiles:
        print("[FAIL] no profiles found", file=sys.stderr)
        return 1

    hermes_failures: list[str] = []
    pf_failures: list[str] = []

    for profile in profiles:
        ok_h, msg_h = hermes_contract(profile)
        ok_pf, msgs_pf = pf_contract(profile)

        status = "PASS" if (ok_h and ok_pf) else "FAIL"
        print(f"[{status}] {profile.name}")
        if not ok_h:
            print(f"        hermes: {msg_h}")
            hermes_failures.append(profile.name)
        if not ok_pf:
            for m in msgs_pf:
                print(f"        pf-runtime: {m}")
            pf_failures.append(profile.name)

    print()
    print(f"Profiles checked: {len(profiles)}")
    print(f"Hermes contract failures: {len(hermes_failures)}")
    print(f"PF Runtime contract failures: {len(pf_failures)}")

    if hermes_failures and pf_failures:
        return 3
    if hermes_failures:
        return 1
    if pf_failures:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
