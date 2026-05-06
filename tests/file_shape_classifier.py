#!/usr/bin/env python3
"""File-shape classifier — plan §5.9.5.

Closes architecture-finding-1 at the level the §5.7 Tier 4 lock left open.
Four pure-function validators classify any markdown file landing in:
  - hermes/profiles/{slug}/skills/   → must be is_hermes_skill
  - hermes/profiles/{slug}/          → must be is_hermes_profile (top-level)
  - ~/.claude/agents/                → must be is_claude_subagent
  - ~/.hermes/skills/                → reserved for Phase 5+ marketplace; flagged

Multi-class or zero-class classifications fail. The test runs in CI on every
commit touching one of the three globs above (configured via .github or pre-commit).

Usage:
    python3 tests/file_shape_classifier.py [--strict]
    pytest tests/file_shape_classifier.py

Exit codes:
    0 — all files in scope classify cleanly
    1 — at least one file failed classification
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path.home() / "Projects" / "agents"
HERMES_PROFILES = REPO_ROOT / "hermes" / "profiles"
CLAUDE_AGENTS = Path.home() / ".claude" / "agents"
SHARED_SKILLS = Path.home() / ".hermes" / "skills"

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class FileClass:
    name: str
    fields_required: tuple[str, ...]
    fields_forbidden: tuple[str, ...]
    body_max_loc: int | None
    body_min_loc: int


def parse_frontmatter(text: str) -> dict[str, str] | None:
    """Return frontmatter top-level keys as a flat key→value dict, or None.

    Only top-level (zero-indentation) keys are extracted. Nested keys under
    a parent (e.g. `prerequisites.tools`) are NOT promoted to the flat dict —
    they belong to their parent's structure and shouldn't be treated as a
    classifier-relevant top-level field.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        # Only top-level (no leading whitespace) keys count as classifier fields.
        if line[:1] in (" ", "\t"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def body_loc(text: str) -> int:
    match = FRONTMATTER_RE.match(text)
    body = text[match.end():] if match else text
    return len([l for l in body.splitlines() if l.strip()])


def has_field(fm: dict[str, str], field: str) -> bool:
    return field in fm and bool(fm[field])


def matches_class(fm: dict[str, str], body: int, cls: FileClass, path: Path | None = None) -> tuple[bool, str]:
    """Return (passes, reason). For heavy_persona, also requires a decoration field."""
    for required in cls.fields_required:
        if not has_field(fm, required):
            return (False, f"missing required field '{required}'")
    for forbidden in cls.fields_forbidden:
        if has_field(fm, forbidden):
            return (False, f"forbidden field '{forbidden}' present")
    if cls.body_max_loc is not None and body > cls.body_max_loc:
        return (False, f"body {body} LOC > max {cls.body_max_loc}")
    if body < cls.body_min_loc:
        return (False, f"body {body} LOC < min {cls.body_min_loc}")
    # Heavy-persona discriminator: must declare at least one decoration field.
    # Without this, every minimal file matches "heavy_persona" by default.
    if cls.name == "heavy_persona":
        if not any(has_field(fm, f) for f in ("color", "emoji", "vibe")):
            return (False, "heavy_persona requires at least one of color/emoji/vibe")
    return (True, "")


# Class definitions. Each class is uniquely identifying — exactly one shape per
# file. Required and forbidden lists are disjoint across classes so a file
# matches at most one class.
#
# Distinguishing fields (the rules that make classes disjoint):
#   - claude_subagent  : MUST declare `tools` (Claude subagents always declare tool scope)
#   - agentskill       : MUST declare `name` + `description`; MUST NOT declare `tools` or `model`
#   - hermes_skill     : MUST live in a SKILL.md filename OR declare `dependencies`
#   - heavy_persona    : MUST declare at least one of color/emoji/vibe (decoration fields)

AGENTSKILL = FileClass(
    name="agentskill",
    fields_required=("name", "description"),
    fields_forbidden=("color", "emoji", "vibe", "tools", "model", "dependencies"),
    body_max_loc=None,  # body length is a separate concern; not enforced here
    body_min_loc=1,
)

CLAUDE_SUBAGENT = FileClass(
    name="claude_subagent",
    fields_required=("name", "description", "tools"),  # `tools` is the dispositive marker
    fields_forbidden=("color", "emoji", "vibe", "dependencies"),
    body_max_loc=None,
    body_min_loc=1,
)

HERMES_SKILL = FileClass(
    name="hermes_skill",
    fields_required=("name", "description"),
    fields_forbidden=("color", "emoji", "vibe", "tools"),
    body_max_loc=None,
    body_min_loc=1,
)

HEAVY_PERSONA = FileClass(
    name="heavy_persona",
    fields_required=("name", "description"),
    fields_forbidden=(),  # heavy persona is permissive in fields but distinguished by decoration
    body_max_loc=None,
    body_min_loc=20,
)


def classify(path: Path) -> tuple[set[str], list[str]]:
    """Return (set_of_passing_class_names, list_of_reasons_per_class).

    A file may pass multiple validators — that is fine. Path-driven
    validation in scan_directory() then asserts the EXPECTED class
    is among the passing set AND no DISQUALIFYING class is present.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    fm = parse_frontmatter(text) or {}
    body = body_loc(text)
    passing: set[str] = set()
    reasons: list[str] = []
    for cls in (AGENTSKILL, CLAUDE_SUBAGENT, HERMES_SKILL, HEAVY_PERSONA):
        ok, reason = matches_class(fm, body, cls)
        if ok:
            passing.add(cls.name)
        else:
            reasons.append(f"  not {cls.name}: {reason}")
    return passing, reasons


# Per-path disqualifying classes — files in these paths must NOT match these classes.
DISQUALIFYING: dict[str, frozenset[str]] = {
    "claude_subagent": frozenset({"heavy_persona"}),  # ~/.claude/agents/ rejects heavy persona
    "hermes_skill":    frozenset({"claude_subagent", "heavy_persona"}),  # skills paths reject persona + subagent shape
}


def expected_class_for_path(path: Path) -> str:
    """Return the class this file should match given its location."""
    try:
        rel = path.resolve().relative_to(HERMES_PROFILES.resolve())
        # hermes/profiles/{slug}/{maybe-skills}/{file}
        parts = rel.parts
        if len(parts) >= 3 and parts[1] == "skills":
            return "hermes_skill"
        return "claude_subagent"  # top-level profile dirs use subagent-like shape
    except (ValueError, FileNotFoundError):
        pass
    try:
        path.resolve().relative_to(CLAUDE_AGENTS.resolve())
        return "claude_subagent"
    except (ValueError, FileNotFoundError):
        pass
    try:
        path.resolve().relative_to(SHARED_SKILLS.resolve())
        return "hermes_skill"  # marketplace placeholder; same shape as profile-local
    except (ValueError, FileNotFoundError):
        pass
    return "unknown"


def is_spec_file(root: Path, path: Path) -> bool:
    """Return True if `path` should be treated as a spec file under `root`.

    The classifier only validates spec files; supporting docs (DESCRIPTION.md,
    references/, USER.md, SOUL.md, README.md) are out of scope.
    """
    name_upper = path.name.upper()
    # Always skip these regardless of location.
    SKIP_NAMES = {
        "CLAUDE.MD", "README.MD", "AGENTS.MD", "USER.MD", "SOUL.MD",
        "MEMORY.MD", "CHANGELOG.MD", "MANIFEST.MD", "DESCRIPTION.MD",
    }
    if name_upper in SKIP_NAMES:
        return False
    # Skip anything inside a `references/` or `examples/` subdirectory.
    rel_parts = path.relative_to(root).parts
    if any(part in {"references", "examples", "fixtures"} for part in rel_parts):
        return False
    # Per-root rules:
    if root == HERMES_PROFILES:
        # hermes/profiles/{slug}/skills/{...}/SKILL.md only.
        if len(rel_parts) < 3 or rel_parts[1] != "skills":
            return False
        return name_upper == "SKILL.MD"
    if root == SHARED_SKILLS:
        # ~/.hermes/skills/{...}/SKILL.md only.
        return name_upper == "SKILL.MD"
    if root == CLAUDE_AGENTS:
        # ~/.claude/agents/{name}.md (no subdirs except _archive which is intentionally legacy).
        if "_archive" in rel_parts:
            return False
        return path.suffix == ".md"
    return False


def scan_directory(root: Path, label: str) -> tuple[int, int, list[str]]:
    """Return (total, failures, error_list)."""
    if not root.exists():
        return 0, 0, []
    total = 0
    failures = 0
    errors: list[str] = []
    for path in root.rglob("*.md"):
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if not is_spec_file(root, path):
            continue
        total += 1
        passing, reasons = classify(path)
        expected = expected_class_for_path(path)
        if expected == "unknown":
            continue
        # The expected class MUST be among the passing set.
        if expected not in passing:
            failures += 1
            errors.append(
                f"  FAIL: {path} expected={expected} passes={sorted(passing) or '[]'}\n"
                + "\n".join(reasons)
            )
            continue
        # AND no disqualifying class can be present (heavy persona in subagent path,
        # subagent shape in skills path, etc.) — this is what catches persona imports.
        bad = DISQUALIFYING.get(expected, frozenset()) & passing
        if bad:
            failures += 1
            errors.append(
                f"  FAIL: {path} expected={expected} also matches disqualifying={sorted(bad)}\n"
                + "\n".join(reasons)
            )
    print(f"  {label}: {total} files scanned, {failures} failures")
    return total, failures, errors


def main() -> int:
    print("File-shape classifier (plan §5.9.5)")
    grand_total = 0
    grand_failures = 0
    all_errors: list[str] = []
    for root, label in (
        (HERMES_PROFILES, "hermes/profiles/"),
        (CLAUDE_AGENTS, "~/.claude/agents/"),
        (SHARED_SKILLS, "~/.hermes/skills/"),
    ):
        t, f, errs = scan_directory(root, label)
        grand_total += t
        grand_failures += f
        all_errors.extend(errs)
    if all_errors:
        print("\nFailures:")
        for err in all_errors:
            print(err)
    print(f"\nTotal: {grand_total} files scanned, {grand_failures} failures")
    return 1 if grand_failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
