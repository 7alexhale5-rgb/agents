#!/usr/bin/env python3
"""Tier 4 read-path isolation contract — plan §5.7.

Asserts that a SkillRegistry constructed for one profile cannot enumerate or
load skills from another profile's directory, the shared ~/.hermes/skills/
path, or anywhere outside hermes/profiles/{slug}/skills/. Closes the
architecture-finding-1 CRITICAL from the post-Phase-4.7.0 swarm review.

This test runs against a stub SkillRegistry that mirrors the contract specified
in pf-runtime/SPEC.md (the §"Tier 4 read-path isolation" section). When the
real SkillRegistry lands in sub-phase 4.7.2, replace the stub import with the
real one — the assertions stay identical.

Usage:
    python3 tests/tier4_isolation.py
    pytest tests/tier4_isolation.py

Exit codes:
    0 — all assertions pass
    1 — at least one assertion fails
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Sequence


REPO_ROOT = Path.home() / "Projects" / "agents"
PROFILES_DIR = REPO_ROOT / "hermes" / "profiles"
SHARED_SKILLS_DIR = Path.home() / ".hermes" / "skills"


class IsolationViolation(Exception):
    """Raised when SkillRegistry would cross a profile boundary."""


class SkillRegistry:
    """Profile-local skill registry stub matching the SPEC.md contract.

    Replace with the production import once pf-runtime/memory/tier4_skills.py
    ships in sub-phase 4.7.2. Until then, this stub IS the contract.
    """

    def __init__(self, profile_slug: str, repo_root: Path = REPO_ROOT):
        if not profile_slug:
            raise ValueError("SkillRegistry requires non-empty profile_slug")
        self.profile_slug = profile_slug
        self.skills_dir = (repo_root / "hermes" / "profiles" / profile_slug / "skills").resolve()

    def list_for_profile(self, profile_slug: str) -> list[Path]:
        if profile_slug != self.profile_slug:
            raise IsolationViolation(
                f"registry for {self.profile_slug} cannot serve {profile_slug}"
            )
        if not self.skills_dir.exists():
            return []
        results: list[Path] = []
        for entry in self.skills_dir.rglob("*.md"):
            resolved = entry.resolve()
            try:
                resolved.relative_to(self.skills_dir)
            except ValueError as exc:
                raise IsolationViolation(
                    f"symlink escape: {entry} → {resolved}"
                ) from exc
            results.append(resolved)
        return results


class BufferStore:
    """Tier 2 stub asserting the matching profile-isolation contract."""

    def __init__(self, profile_slug: str | None):
        if not profile_slug:
            raise ValueError("BufferStore requires non-empty profile_slug")
        self.profile_slug = profile_slug


def _passes(name: str) -> None:
    print(f"  PASS: {name}")


def _fails(name: str, detail: str) -> None:
    print(f"  FAIL: {name} — {detail}")


def assertion_1_profile_local_only() -> bool:
    """SkillRegistry.list_for_profile('personal') returns only files under
    hermes/profiles/personal/skills/."""
    name = "1. personal registry returns only personal/skills/"
    reg = SkillRegistry("personal")
    expected_root = (PROFILES_DIR / "personal" / "skills").resolve()
    listed = reg.list_for_profile("personal")
    for path in listed:
        try:
            path.relative_to(expected_root)
        except ValueError:
            _fails(name, f"path {path} escapes {expected_root}")
            return False
    _passes(name)
    return True


def assertion_2_shared_path_invisible() -> bool:
    """A planted decoy file in ~/.hermes/skills/ does NOT appear in any
    per-profile registry call."""
    name = "2. shared ~/.hermes/skills/ is invisible to per-profile registry"
    SHARED_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    decoy = SHARED_SKILLS_DIR / "decoy_isolation_test.md"
    decoy_created = not decoy.exists()
    try:
        if decoy_created:
            decoy.write_text("---\nname: decoy\n---\nLEAK\n")
        for slug in [p.name for p in PROFILES_DIR.iterdir() if p.is_dir()]:
            reg = SkillRegistry(slug)
            for path in reg.list_for_profile(slug):
                if "decoy_isolation_test" in path.name:
                    _fails(name, f"decoy leaked into {slug}'s registry")
                    return False
    finally:
        if decoy_created and decoy.exists():
            decoy.unlink()
    _passes(name)
    return True


def assertion_3_symlink_escape_rejected() -> bool:
    """A symlink from hermes/profiles/personal/skills/escape.md to /tmp/poison.md
    raises IsolationViolation."""
    name = "3. symlink escape raises IsolationViolation"
    skills_dir = PROFILES_DIR / "personal" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    poison = Path(tempfile.gettempdir()) / "poison_isolation_test.md"
    escape = skills_dir / "escape_isolation_test.md"
    poison.write_text("---\nname: poison\n---\nLEAK\n")
    escape.symlink_to(poison)
    reg = SkillRegistry("personal")
    try:
        reg.list_for_profile("personal")
    except IsolationViolation:
        _passes(name)
        escape.unlink()
        poison.unlink()
        return True
    finally:
        if escape.exists() or escape.is_symlink():
            escape.unlink()
        if poison.exists():
            poison.unlink()
    _fails(name, "symlink escape was NOT rejected")
    return False


def assertion_4_buffer_store_requires_profile_slug() -> bool:
    """BufferStore(profile_slug=None) raises ValueError at construction."""
    name = "4. BufferStore(profile_slug=None) raises ValueError"
    try:
        BufferStore(profile_slug=None)  # type: ignore[arg-type]
    except ValueError:
        _passes(name)
        return True
    _fails(name, "constructor accepted profile_slug=None")
    return False


def assertion_5_cross_profile_call_rejected() -> bool:
    """A registry constructed for profile A cannot serve profile B."""
    name = "5. cross-profile call raises IsolationViolation"
    profiles = [p.name for p in PROFILES_DIR.iterdir() if p.is_dir()]
    if len(profiles) < 2:
        _fails(name, f"need ≥2 profile dirs to test cross-profile call (found {len(profiles)})")
        return False
    a, b = profiles[0], profiles[1]
    reg = SkillRegistry(a)
    try:
        reg.list_for_profile(b)
    except IsolationViolation:
        _passes(name)
        return True
    _fails(name, f"registry for {a} served {b} without raising")
    return False


def main() -> int:
    print("Tier 4 read-path isolation contract (plan §5.7)")
    results: Sequence[bool] = [
        assertion_1_profile_local_only(),
        assertion_2_shared_path_invisible(),
        assertion_3_symlink_escape_rejected(),
        assertion_4_buffer_store_requires_profile_slug(),
        assertion_5_cross_profile_call_rejected(),
    ]
    failures = sum(1 for r in results if not r)
    if failures:
        print(f"\n{failures}/{len(results)} assertions failed")
        return 1
    print(f"\nAll {len(results)} assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
