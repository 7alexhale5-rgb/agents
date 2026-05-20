#!/usr/bin/env python3
"""Validate converted Agency shared skills."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path("/Users/alexhale/Projects/agents")
AGENCY_ROOT = REPO_ROOT / "hermes/shared-skills/agency"
CATALOG_JSON = AGENCY_ROOT / "catalog.json"
TRIGGER_MATRIX = AGENCY_ROOT / "TRIGGER-MATRIX.md"
ARSENAL_MAP = AGENCY_ROOT / "ARSENAL-MAP.md"


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    meta: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip()
    return meta


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    if not CATALOG_JSON.exists():
        fail(errors, f"missing {CATALOG_JSON}")
        print("\n".join(errors))
        return 1

    catalog = json.loads(CATALOG_JSON.read_text(encoding="utf-8"))
    converted = [
        item["skill"]
        for item in catalog["items"]
        if item.get("status") in {"converted", "converted-curated"}
    ]
    converted = [skill for skill in converted if skill]
    if len(converted) < 60:
        fail(errors, f"expected at least 60 converted skills, found {len(converted)}")
    for item in catalog["items"]:
        if not item.get("owner"):
            fail(errors, f"{item.get('relpath')}: missing owner")
        if not item.get("fit"):
            fail(errors, f"{item.get('relpath')}: missing fit")

    for skill in converted:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill):
            fail(errors, f"{skill}: name is not kebab-case")
        skill_file = AGENCY_ROOT / skill / "SKILL.md"
        if not skill_file.exists():
            fail(errors, f"{skill}: missing SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        meta = parse_frontmatter(text)
        if meta.get("name") != skill:
            fail(errors, f"{skill}: frontmatter name mismatch")
        desc = meta.get("description", "")
        if len(desc) < 80 or "Use when" not in desc:
            fail(errors, f"{skill}: description is not a concise trigger")
        for section in [
            "## Use When",
            "## Inputs",
            "## Procedure",
            "## Output Contract",
            "## Constraints",
            "## Validation",
            "## Source Attribution",
        ]:
            if section not in text:
                fail(errors, f"{skill}: missing {section}")
        if "MIT" not in text or "msitarzewski/agency-agents" not in text:
            fail(errors, f"{skill}: missing source attribution")
        forbidden = [
            "You are **",
            "Your Identity",
            "Your Core Mission",
            "never sleep",
            "activate ",
        ]
        lowered = text.lower()
        for term in forbidden:
            if term.lower() in lowered:
                fail(errors, f"{skill}: persona/agent framing leaked: {term}")

    if not TRIGGER_MATRIX.exists():
        fail(errors, f"missing {TRIGGER_MATRIX}")
    else:
        trigger_text = TRIGGER_MATRIX.read_text(encoding="utf-8")
        for skill in converted:
            if f"`{skill}`" not in trigger_text:
                fail(errors, f"{skill}: missing trigger-matrix row")
        for forbidden in ["Activate ", " agent mode", " profile mode"]:
            if forbidden.lower() in trigger_text.lower():
                fail(errors, f"trigger matrix contains persona/profile cue: {forbidden.strip()}")
    if not ARSENAL_MAP.exists():
        fail(errors, f"missing {ARSENAL_MAP}")
    else:
        arsenal_text = ARSENAL_MAP.read_text(encoding="utf-8")
        for required in ["## Every Active Skill", "## Every Agency Catalog Skill Addressed", "## Visual Fit Map"]:
            if required not in arsenal_text:
                fail(errors, f"arsenal map missing section: {required}")

    # Spot checks from the implementation plan.
    for skill in [
        "marketing-ai-citation-strategist",
        "design-whimsy-injector",
        "testing-reality-checker",
        "specialized-compliance-auditor",
        "finance-tax-strategist",
    ]:
        path = AGENCY_ROOT / skill / "SKILL.md"
        if not path.exists():
            fail(errors, f"spot check missing converted skill: {skill}")
            continue
        text = path.read_text(encoding="utf-8")
        if "Source Attribution" not in text:
            fail(errors, f"spot check {skill}: missing attribution")
        if skill in {"specialized-compliance-auditor", "finance-tax-strategist"}:
            if "current-source verification" not in text:
                fail(errors, f"spot check {skill}: missing current-source gate")

    if errors:
        print("Agency skill validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Agency skill validation PASS ({len(converted)} converted skills)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
