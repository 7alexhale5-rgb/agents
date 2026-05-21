#!/usr/bin/env python3
"""Build Hermes shared skills from the Agency agent catalog.

This intentionally converts agents into procedural skills, not personas.
The upstream catalog is cloned outside this repo and remains the source input.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path("/Users/alexhale/Projects/agents")
UPSTREAM_ROOT = Path("/tmp/agency-agents")
AGENCY_ROOT = REPO_ROOT / "hermes/shared-skills/agency"
CATALOG_MD = AGENCY_ROOT / "CATALOG.md"
ARSENAL_MAP_MD = AGENCY_ROOT / "ARSENAL-MAP.md"
TRIGGER_MATRIX_MD = AGENCY_ROOT / "TRIGGER-MATRIX.md"
CATALOG_JSON = AGENCY_ROOT / "catalog.json"
ARTIFACT_MD = Path(
    "/Users/alexhale/Projects/memory-vault/operator-artifacts/"
    "agency-skills-conversion-20260520.md"
)
HTML_RENDERER = Path("/Users/alexhale/.claude/scripts/operator-md-to-html.py")


P1_PATHS = {
    "design/design-brand-guardian.md",
    "design/design-image-prompt-engineer.md",
    "design/design-inclusive-visuals-specialist.md",
    "design/design-ui-designer.md",
    "design/design-ux-architect.md",
    "design/design-ux-researcher.md",
    "design/design-visual-storyteller.md",
    "design/design-whimsy-injector.md",
    "engineering/engineering-backend-architect.md",
    "engineering/engineering-code-reviewer.md",
    "engineering/engineering-codebase-onboarding-engineer.md",
    "engineering/engineering-data-engineer.md",
    "engineering/engineering-database-optimizer.md",
    "engineering/engineering-devops-automator.md",
    "engineering/engineering-email-intelligence-engineer.md",
    "engineering/engineering-frontend-developer.md",
    "engineering/engineering-incident-response-commander.md",
    "engineering/engineering-security-engineer.md",
    "engineering/engineering-software-architect.md",
    "engineering/engineering-sre.md",
    "engineering/engineering-technical-writer.md",
    "engineering/engineering-threat-detection-engineer.md",
    "marketing/marketing-agentic-search-optimizer.md",
    "marketing/marketing-ai-citation-strategist.md",
    "marketing/marketing-content-creator.md",
    "marketing/marketing-linkedin-content-creator.md",
    "marketing/marketing-podcast-strategist.md",
    "marketing/marketing-reddit-community-builder.md",
    "marketing/marketing-seo-specialist.md",
    "marketing/marketing-social-media-strategist.md",
    "marketing/marketing-twitter-engager.md",
    "paid-media/paid-media-auditor.md",
    "paid-media/paid-media-creative-strategist.md",
    "paid-media/paid-media-paid-social-strategist.md",
    "paid-media/paid-media-ppc-strategist.md",
    "paid-media/paid-media-programmatic-buyer.md",
    "paid-media/paid-media-search-query-analyst.md",
    "paid-media/paid-media-tracking-specialist.md",
    "product/product-behavioral-nudge-engine.md",
    "product/product-feedback-synthesizer.md",
    "product/product-manager.md",
    "product/product-sprint-prioritizer.md",
    "product/product-trend-researcher.md",
    "sales/sales-account-strategist.md",
    "sales/sales-coach.md",
    "sales/sales-deal-strategist.md",
    "sales/sales-discovery-coach.md",
    "sales/sales-engineer.md",
    "sales/sales-outbound-strategist.md",
    "sales/sales-pipeline-analyst.md",
    "sales/sales-proposal-strategist.md",
    "specialized/automation-governance-architect.md",
    "specialized/lsp-index-engineer.md",
    "specialized/specialized-mcp-builder.md",
    "specialized/specialized-model-qa.md",
    "testing/testing-accessibility-auditor.md",
    "testing/testing-api-tester.md",
    "testing/testing-evidence-collector.md",
    "testing/testing-performance-benchmarker.md",
    "testing/testing-reality-checker.md",
    "testing/testing-test-results-analyzer.md",
    "testing/testing-tool-evaluator.md",
    "testing/testing-workflow-optimizer.md",
}

CURATED_CONVERT_PATHS = {
    "finance/finance-tax-strategist.md",
    "specialized/compliance-auditor.md",
}

DO_NOT_CONVERT = {
    "specialized/agents-orchestrator.md",
    "specialized/specialized-chief-of-staff.md",
}

PROFILE_ENABLEMENT = {
    "atlas-ceo": [
        "product-behavioral-nudge-engine",
        "product-feedback-synthesizer",
        "product-manager",
        "product-sprint-prioritizer",
        "product-trend-researcher",
        "sales-pipeline-analyst",
        "specialized-compliance-auditor",
        "finance-tax-strategist",
    ],
    "marin": [
        "marketing-agentic-search-optimizer",
        "marketing-ai-citation-strategist",
        "marketing-linkedin-content-creator",
        "marketing-seo-specialist",
        "sales-account-strategist",
        "sales-coach",
        "sales-deal-strategist",
        "sales-discovery-coach",
        "sales-engineer",
        "sales-outbound-strategist",
        "sales-pipeline-analyst",
        "sales-proposal-strategist",
    ],
    "quill": [
        "design-brand-guardian",
        "design-image-prompt-engineer",
        "design-inclusive-visuals-specialist",
        "design-visual-storyteller",
        "marketing-content-creator",
        "marketing-linkedin-content-creator",
    ],
    "stet": [
        "design-brand-guardian",
        "specialized-compliance-auditor",
        "testing-accessibility-auditor",
        "testing-evidence-collector",
        "testing-performance-benchmarker",
        "testing-reality-checker",
        "testing-test-results-analyzer",
        "testing-tool-evaluator",
    ],
}

PARKED_CANDIDATES = {
    "technical-operator": [
        "engineering-backend-architect",
        "engineering-code-reviewer",
        "engineering-codebase-onboarding-engineer",
        "engineering-data-engineer",
        "engineering-database-optimizer",
        "engineering-devops-automator",
        "engineering-email-intelligence-engineer",
        "engineering-frontend-developer",
        "engineering-incident-response-commander",
        "engineering-security-engineer",
        "engineering-software-architect",
        "engineering-sre",
        "engineering-technical-writer",
        "engineering-threat-detection-engineer",
        "specialized-automation-governance-architect",
        "specialized-lsp-index-engineer",
        "specialized-mcp-builder",
        "specialized-model-qa",
        "testing-api-tester",
        "testing-workflow-optimizer",
    ],
    "channel-triggered": [
        "marketing-reddit-community-builder",
        "marketing-social-media-strategist",
        "marketing-twitter-engager",
        "paid-media-auditor",
        "paid-media-creative-strategist",
        "paid-media-paid-social-strategist",
        "paid-media-ppc-strategist",
        "paid-media-programmatic-buyer",
        "paid-media-search-query-analyst",
        "paid-media-tracking-specialist",
    ],
    "artifact-triggered": [
        "design-ui-designer",
        "design-ux-architect",
        "design-ux-researcher",
        "design-whimsy-injector",
        "marketing-podcast-strategist",
    ],
}

PROFILE_LABELS = {
    "atlas-ceo": "Atlas CEO",
    "marin": "Marin",
    "quill": "Quill",
    "stet": "Stet",
}

PROFILE_FIT = {
    "atlas-ceo": "executive decision support",
    "marin": "marketing strategy, pipeline, and revenue-loop decisions",
    "quill": "drafting, brand, content, and creative production support",
    "stet": "pre-launch critique, verification, and risk review",
}

PARKED_LABELS = {
    "technical-operator": "Parked for future technical-operator",
    "channel-triggered": "Parked until channel/tool trigger",
    "artifact-triggered": "Parked until artifact trigger",
}

PARKED_FIT = {
    "technical-operator": "future CTO / technical governance candidate; not active profile ownership",
    "channel-triggered": "valid workflow parked until the current revenue loop authorizes the channel or spend surface",
    "artifact-triggered": "valid creative/product workflow parked until a specific artifact needs it",
}

DISABLED_PROFILE_NOTES = {"codex"}

HIGH_STAKES_TERMS = (
    "tax",
    "legal",
    "healthcare",
    "compliance",
    "blockchain-security",
    "solidity",
    "loan",
    "real-estate",
    "accounts-payable",
    "finance-bookkeeper",
    "investment",
    "civil-engineer",
    "government",
    "identity-trust",
    "identity-graph",
)

EXECUTION_HEAVY_TERMS = (
    "frontend-developer",
    "mobile-app-builder",
    "rapid-prototyper",
    "senior-developer",
    "cms-developer",
    "embedded",
    "wechat",
    "feishu",
    "voice-ai",
    "game-development",
    "spatial-computing",
    "blender",
    "godot",
    "roblox",
    "unity",
    "unreal",
    "visionos",
    "xr-",
    "avatar-creator",
)

MARKET_SPECIFIC_TERMS = (
    "baidu",
    "bilibili",
    "douyin",
    "kuaishou",
    "weibo",
    "xiaohongshu",
    "zhihu",
    "china",
    "korean",
    "french",
    "avatar-creator",
)

INFRA_TERMS = (
    "sre",
    "incident",
    "devops",
    "security-engineer",
    "threat-detection",
    "database-optimizer",
    "backend-architect",
    "software-architect",
    "data-engineer",
    "email-intelligence",
    "lsp-index",
    "mcp-builder",
    "automation-governance",
)

PRODUCT_MARKETING_TERMS = (
    "ai-citation",
    "agentic-search",
    "seo",
    "content",
    "linkedin",
    "reddit",
    "social-media",
    "campaign",
    "brand",
    "ux",
    "ui-designer",
    "whimsy",
    "inclusive",
    "image-prompt",
    "paid-media",
    "sales-",
    "product-",
    "proposal",
    "discovery",
    "pipeline",
)

TESTING_TERMS = (
    "testing-",
    "code-reviewer",
    "codebase-onboarding",
    "technical-writer",
    "accessibility",
    "performance-benchmarker",
    "reality-checker",
    "evidence-collector",
    "api-tester",
    "tool-evaluator",
    "workflow-optimizer",
    "model-qa",
)


@dataclass(frozen=True)
class AgencyItem:
    relpath: str
    division: str
    slug: str
    name: str
    description: str
    bucket: str
    priority: str
    status: str
    reason: str
    source_path: Path


@dataclass(frozen=True)
class ArsenalSkill:
    name: str
    owner: str
    source: str
    fit: str
    status: str
    kind: str
    path: str


def skill_slug_for(relpath: str) -> str:
    division = relpath.split("/", 1)[0]
    stem = Path(relpath).stem
    if stem.startswith(f"{division}-"):
        return stem
    if division in {"specialized", "support", "academic"}:
        return f"{division}-{stem}"
    return stem


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.check_output(cmd, cwd=cwd, text=True).strip()


def markdown_cell(value: str) -> str:
    value = clean_text(value)
    value = value.replace("|", "\\|")
    return value


def owners_for_skill(skill: str) -> list[str]:
    owners = [profile for profile, skills in PROFILE_ENABLEMENT.items() if skill in skills]
    return owners or ["unassigned"]


def parked_bucket_for_skill(skill: str) -> str | None:
    for bucket, skills in PARKED_CANDIDATES.items():
        if skill in skills:
            return bucket
    return None


def owner_label(owners: list[str]) -> str:
    labels = [PROFILE_LABELS.get(owner, owner) for owner in owners]
    return ", ".join(labels)


def fit_for_agency_item(item: AgencyItem) -> str:
    if item.status == "blocked-role-boundary":
        return "Do not convert; this is a coordinator or identity role, not procedural memory."
    if item.status == "deferred":
        return "Reference-only until a live project or client workflow needs it."
    if item.bucket == "curate":
        return "Advisory/readiness skill with current-source gates and human review."
    if item.status.startswith("converted"):
        parked_bucket = parked_bucket_for_skill(item.slug)
        if parked_bucket:
            return PARKED_FIT[parked_bucket]
        owners = owners_for_skill(item.slug)
        return "Owned by " + owner_label(owners) + " for " + "; ".join(
            PROFILE_FIT.get(owner, owner) for owner in owners if owner != "unassigned"
        )
    return "Convertible later as a shared workflow; not installed into profile manifests yet."


def recommended_owner_for_item(item: AgencyItem) -> str:
    if item.status.startswith("converted"):
        parked_bucket = parked_bucket_for_skill(item.slug)
        if parked_bucket:
            return PARKED_LABELS[parked_bucket]
        return owner_label(owners_for_skill(item.slug))
    if item.status == "blocked-role-boundary":
        return "No owner - keep as profile/agent boundary reference"
    div = item.division
    if div in {"engineering", "testing", "spatial-computing", "game-development"}:
        return "Future technical-operator candidate"
    if div in {"marketing", "paid-media", "sales"}:
        return "Marin"
    if div == "design":
        return "Quill, Stet"
    if div == "product":
        return "Atlas CEO, Marin"
    if div in {"finance", "support", "project-management"}:
        return "Atlas CEO"
    if div in {"academic", "specialized"}:
        return "Atlas CEO or future technical-operator by request"
    return "Unassigned"


def ensure_upstream() -> str:
    if not (UPSTREAM_ROOT / ".git").exists():
        run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "https://github.com/msitarzewski/agency-agents.git",
                str(UPSTREAM_ROOT),
            ]
        )
    return run(["git", "rev-parse", "--short", "HEAD"], cwd=UPSTREAM_ROOT)


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
        meta[key.strip()] = value.strip().strip('"')
    return meta


def discover_items(upstream_commit: str) -> list[AgencyItem]:
    files = sorted(
        p
        for p in UPSTREAM_ROOT.rglob("*.md")
        if "/.github/" not in str(p)
        and "/examples/" not in str(p)
        and "/integrations/" not in str(p)
        and "/strategy/" not in str(p)
        and "/scripts/" not in str(p)
        and p.name not in {"README.md", "CONTRIBUTING.md", "SECURITY.md"}
    )
    items: list[AgencyItem] = []
    for path in files:
        relpath = path.relative_to(UPSTREAM_ROOT).as_posix()
        text = path.read_text(errors="replace")
        meta = parse_frontmatter(text)
        if not meta.get("name"):
            continue
        hay = f"{relpath} {meta.get('name', '')} {meta.get('description', '')}".lower()
        bucket = "convert"
        priority = "P2"
        reason = "procedural workflow can become a reusable skill"

        if any(term in hay for term in HIGH_STAKES_TERMS):
            bucket = "curate"
            priority = "P3"
            reason = "high-stakes or regulated; convert only as advisory/readiness with source/current-law gates"
        if any(term in hay for term in EXECUTION_HEAVY_TERMS):
            bucket = "defer"
            priority = "P4"
            reason = "execution-heavy role; defer until tied to a live project need"
        if any(term in hay for term in INFRA_TERMS):
            bucket = "convert"
            priority = "P1"
            reason = "high-leverage engineering/reliability workflow; good skill candidate with checklist and validation commands"
        if any(term in hay for term in TESTING_TERMS):
            bucket = "convert"
            priority = "P1"
            reason = "review/test/evidence workflow maps cleanly to skill"
        if any(term in hay for term in PRODUCT_MARKETING_TERMS):
            bucket = "convert"
            if relpath.split("/", 1)[0] in {"marketing", "sales", "product", "paid-media", "design"}:
                priority = "P1"
            reason = "directly useful to current revenue motion; convert as bounded workflow"
        if any(term in hay for term in MARKET_SPECIFIC_TERMS):
            bucket = "defer"
            priority = "P4"
            reason = "market-specific channel role; keep as reference until a campaign/client needs it"
        if relpath.split("/", 1)[0] == "support":
            bucket = "curate"
            priority = "P3"
            reason = "business-ops workflow; convert only if tied to a profile or client workflow"
        if relpath in DO_NOT_CONVERT:
            bucket = "do_not_convert"
            priority = "P5"
            reason = "true coordinator/identity role; violates skill-vs-agent boundary"
        if relpath in P1_PATHS:
            bucket = "convert"
            priority = "P1"
            reason = "P1 revenue, review, testing, reliability, or technical governance workflow"
        if relpath in CURATED_CONVERT_PATHS:
            bucket = "curate"
            priority = "P3"
            reason = "curated high-stakes advisory skill with explicit source/current-law gates"

        status = "converted" if relpath in P1_PATHS else "cataloged"
        if relpath in CURATED_CONVERT_PATHS:
            status = "converted-curated"
        if relpath in DO_NOT_CONVERT:
            status = "blocked-role-boundary"
        elif bucket == "defer":
            status = "deferred"

        items.append(
            AgencyItem(
                relpath=relpath,
                division=relpath.split("/", 1)[0],
                slug=skill_slug_for(relpath),
                name=meta["name"],
                description=meta.get("description", ""),
                bucket=bucket,
                priority=priority,
                status=status,
                reason=f"{reason}; upstream {upstream_commit}",
                source_path=path,
            )
        )
    return items


def clean_text(value: str) -> str:
    value = re.sub(r"[\U00010000-\U0010ffff]", "", value)
    value = value.replace("—", "-").replace("–", "-").replace("’", "'")
    value = value.replace("“", '"').replace("”", '"')
    value = re.sub(r"\s+", " ", value).strip()
    return value


def output_contract(item: AgencyItem) -> str:
    div = item.division
    if div in {"marketing", "paid-media", "sales"}:
        return (
            "Return an advisory memo or worksheet only. Include source notes, assumptions, "
            "risks, and the smallest next manual action. Do not publish, send, schedule, "
            "spend, scrape at scale, or create unattended outreach."
        )
    if div == "testing":
        return (
            "Return an evidence-first verdict with commands run, artifacts inspected, "
            "blocking gaps, and the exact evidence needed to certify the work."
        )
    if div == "engineering" or item.slug.startswith("specialized-"):
        return (
            "Return an implementation/review plan, checklist, or findings report. Include "
            "validation commands and avoid changing files unless the invoking agent has "
            "separate execution authority."
        )
    if div == "design":
        return (
            "Return a design critique or proposal with concrete surfaces, rationale, and "
            "acceptance checks. Do not invent brand rules; cite the available brand source."
        )
    if div == "product":
        return (
            "Return a decision memo, prioritization table, or synthesis brief with evidence, "
            "tradeoffs, and one recommended next move."
        )
    if item.slug == "finance-tax-strategist":
        return (
            "Return advisory planning notes only. Require current jurisdiction facts and "
            "recommend professional review before tax positions, filings, elections, or entity changes."
        )
    return "Return a concise workflow artifact with sources, assumptions, risks, and validation steps."


def constraints(item: AgencyItem) -> list[str]:
    base = [
        "Use this as a skill workflow, not as a persona or standalone agent.",
        "Do not create new Hermes profiles, dispatch agents, or claim persistent memory.",
        "Do not add external-send, publishing, money-movement, or unattended automation authority.",
        "State missing inputs instead of inventing facts, metrics, legal requirements, or source evidence.",
    ]
    if item.bucket == "curate" or any(term in item.relpath for term in HIGH_STAKES_TERMS):
        base.extend(
            [
                "Treat this as advisory/readiness support only, not professional legal, medical, tax, financial, or compliance advice.",
                "For current law, regulatory, platform, or standards claims, perform current-source verification against primary/current sources before relying on them.",
            ]
        )
    return base


def trigger_prompt(item: AgencyItem) -> str:
    topic = item.name.lower()
    return f"Use the {topic} skill to assess this request and return the required artifact without adopting a persona."


def write_skill(item: AgencyItem, upstream_commit: str) -> None:
    skill_dir = AGENCY_ROOT / item.slug
    skill_dir.mkdir(parents=True, exist_ok=True)
    desc = clean_text(item.description)
    body = [
        "---",
        f"name: {item.slug}",
        (
            "description: "
            f"Use when a Hermes profile needs the Agency-derived {item.name} workflow. "
            f"{desc}"
        ),
        "---",
        "",
        f"# {item.name}",
        "",
        "This is a converted Agency catalog workflow. Use it as procedural support inside an existing Hermes profile; do not adopt the original agent persona.",
        "",
        "## Use When",
        "",
        f"- The request asks for {item.name.lower()} style help, assessment, planning, critique, or artifact production.",
        f"- The active profile has opted into `{item.slug}` in `hermes/shared-skills/agency/CATALOG.md`.",
        "- The work can remain proposal-only, read-only, or manually reviewed by Alex.",
        "",
        "## Inputs",
        "",
        "- User goal and success criteria.",
        "- Relevant source files, URLs, screenshots, metrics, logs, or evidence package.",
        "- Explicit constraints: audience, scope, deadline, brand/compliance rules, and what must not happen.",
        "- Current date and source freshness when claims may change over time.",
        "",
        "## Procedure",
        "",
        "1. Restate the task as a bounded workflow and name any missing inputs.",
        "2. Gather only the sources needed for the requested artifact; prefer repo/vault truth over generic advice.",
        "3. Apply the upstream workflow shape from the Agency source, but remove persona language and unsupported authority.",
        "4. Produce the deliverable in the output contract below.",
        "5. Run the validation checks and clearly mark any unresolved risk.",
        "",
        "## Output Contract",
        "",
        output_contract(item),
        "",
        "## Constraints",
        "",
    ]
    body.extend(f"- {line}" for line in constraints(item))
    body.extend(
        [
            "",
            "## Validation",
            "",
            "- Every factual claim has a source, input, or explicit assumption.",
            "- The output contains a clear verdict, recommendation, or next manual action.",
            "- The output does not claim execution, persistence, external sending, publishing, or spend.",
            "- High-stakes claims are caveated and require current-source verification before action.",
            "",
            "## Source Attribution",
            "",
            f"- Adapted from `{item.relpath}` in `msitarzewski/agency-agents` at commit `{upstream_commit}`.",
            "- Original catalog license: MIT.",
            "- Conversion note: persona, memory, and autonomous-agent framing were intentionally removed.",
            "",
        ]
    )
    (skill_dir / "SKILL.md").write_text("\n".join(body), encoding="utf-8")


def write_catalog(items: list[AgencyItem], upstream_commit: str) -> None:
    AGENCY_ROOT.mkdir(parents=True, exist_ok=True)
    converted = [i for i in items if i.status.startswith("converted")]
    counts = {
        "total": len(items),
        "converted": len([i for i in items if i.status == "converted"]),
        "converted_curated": len([i for i in items if i.status == "converted-curated"]),
        "deferred": len([i for i in items if i.status == "deferred"]),
        "blocked": len([i for i in items if i.status == "blocked-role-boundary"]),
    }
    catalog_rows = [
        "# Agency Shared Skills Catalog",
        "",
        f"Source: `msitarzewski/agency-agents` commit `{upstream_commit}`.",
        "",
        "This catalog converts Agency roles into Hermes shared skills. Profiles opt into a subset; no Agency file creates a new Hermes profile or autonomous subagent.",
        "",
        "## Counts",
        "",
        f"- Total upstream agent files: {counts['total']}",
        f"- P1 converted skills: {counts['converted']}",
        f"- Curated high-stakes converted skills: {counts['converted_curated']}",
        f"- Deferred/reference-only: {counts['deferred']}",
        f"- Blocked by skill-vs-agent boundary: {counts['blocked']}",
        "",
        "## Profile Enablement",
        "",
    ]
    for profile, skills in PROFILE_ENABLEMENT.items():
        catalog_rows.append(f"- `{profile}`: " + ", ".join(f"`{s}`" for s in skills))
    catalog_rows.extend(["", "## Parked Candidates", ""])
    for bucket, skills in PARKED_CANDIDATES.items():
        catalog_rows.append(
            f"- **{PARKED_LABELS[bucket]}**: " + ", ".join(f"`{s}`" for s in skills)
        )
    catalog_rows.extend(
        [
            "",
            "## Full Classification Matrix",
            "",
            "| Division | Source | Skill | Owner | Fit | Priority | Bucket | Status | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in items:
        skill = item.slug if item.status.startswith("converted") else ""
        catalog_rows.append(
            f"| {item.division} | `{item.relpath}` | `{skill}` | "
            f"{markdown_cell(recommended_owner_for_item(item))} | {markdown_cell(fit_for_agency_item(item))} | "
            f"{item.priority} | {item.bucket} | {item.status} | {markdown_cell(item.reason)} |"
        )
    CATALOG_MD.write_text("\n".join(catalog_rows) + "\n", encoding="utf-8")

    trigger_rows = [
        "# Agency Shared Skills Trigger Matrix",
        "",
        "Static smoke-test prompts. Each converted skill has one prompt that should trigger the skill workflow without asking the model to become a persona/profile.",
        "",
        "| Skill | Source | Smoke Prompt |",
        "| --- | --- | --- |",
    ]
    for item in converted:
        trigger_rows.append(f"| `{item.slug}` | `{item.relpath}` | {trigger_prompt(item)} |")
    TRIGGER_MATRIX_MD.write_text("\n".join(trigger_rows) + "\n", encoding="utf-8")

    CATALOG_JSON.write_text(
        json.dumps(
            {
                "source": "https://github.com/msitarzewski/agency-agents",
                "source_commit": upstream_commit,
                "counts": counts,
                "profile_enablement": PROFILE_ENABLEMENT,
                "parked_candidates": PARKED_CANDIDATES,
                "items": [
                    {
                        "relpath": i.relpath,
                        "division": i.division,
                        "skill": i.slug if i.status.startswith("converted") else None,
                        "priority": i.priority,
                        "bucket": i.bucket,
                        "status": i.status,
                        "reason": i.reason,
                        "owner": recommended_owner_for_item(i),
                        "fit": fit_for_agency_item(i),
                    }
                    for i in items
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def skill_name_from_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    meta = parse_frontmatter(text)
    return meta.get("name") or path.stem


def discover_active_arsenal(items: list[AgencyItem]) -> list[ArsenalSkill]:
    arsenal: list[ArsenalSkill] = []

    for profile_dir in sorted((REPO_ROOT / "hermes/profiles").glob("*")):
        skills_dir = profile_dir / "skills"
        if not skills_dir.exists():
            continue
        for path in sorted(skills_dir.glob("*.md")):
            if path.name == "README.md":
                continue
            name = skill_name_from_file(path)
            owner = profile_dir.name
            rel = path.relative_to(REPO_ROOT).as_posix()
            arsenal.append(
                ArsenalSkill(
                    name=name,
                    owner=PROFILE_LABELS.get(owner, owner),
                    source="profile-local",
                    fit=PROFILE_FIT.get(owner, "profile-local procedure"),
                    status="active",
                    kind="Hermes profile skill",
                    path=rel,
                )
            )

    for path in sorted((REPO_ROOT / "hermes/shared-skills").glob("*/SKILL.md")):
        if "/agency/" in path.as_posix():
            continue
        name = skill_name_from_file(path)
        rel = path.relative_to(REPO_ROOT).as_posix()
        owner = "All profiles" if name == "generate-handoff" else "Koho/Yeh future retainer profiles"
        fit = "cross-session continuity" if name == "generate-handoff" else "read-only communications triage and proposal store"
        arsenal.append(
            ArsenalSkill(
                name=name,
                owner=owner,
                source="shared",
                fit=fit,
                status="active",
                kind="Hermes shared skill",
                path=rel,
            )
        )

    for path in sorted((REPO_ROOT / "hermes/skills").glob("*/SKILL.md")):
        name = skill_name_from_file(path)
        rel = path.relative_to(REPO_ROOT).as_posix()
        arsenal.append(
            ArsenalSkill(
                name=name,
                owner="Fleet builder",
                source="platform",
                fit="profile scaffolding and capability creation",
                status="active",
                kind="Hermes platform skill",
                path=rel,
            )
        )

    agency_by_slug = {item.slug: item for item in items if item.status.startswith("converted")}
    for slug, item in sorted(agency_by_slug.items()):
        parked_bucket = parked_bucket_for_skill(slug)
        arsenal.append(
            ArsenalSkill(
                name=slug,
                owner=PARKED_LABELS[parked_bucket] if parked_bucket else owner_label(owners_for_skill(slug)),
                source="agency-shared",
                fit=fit_for_agency_item(item),
                status="parked-candidate" if parked_bucket else item.status,
                kind="Agency-derived shared skill",
                path=f"hermes/shared-skills/agency/{slug}/SKILL.md",
            )
        )

    return sorted(arsenal, key=lambda s: (s.source, s.owner, s.name))


def write_arsenal_map(items: list[AgencyItem], upstream_commit: str) -> None:
    active = discover_active_arsenal(items)
    source_counts: dict[str, int] = {}
    owner_counts: dict[str, int] = {}
    for skill in active:
        source_counts[skill.source] = source_counts.get(skill.source, 0) + 1
        owner_counts[skill.owner] = owner_counts.get(skill.owner, 0) + 1

    lines = [
        "# Hermes Skill Arsenal Map",
        "",
        f"Source snapshot: `msitarzewski/agency-agents` `{upstream_commit}`.",
        "",
        "This is the ownership view for the current skill arsenal. It covers profile-local Hermes skills, shared Hermes skills, platform scaffolding skills, and the Agency-derived shared skills.",
        "",
        "## Visual Fit Map",
        "",
        "```mermaid",
        "flowchart TB",
        '  agency["Agency catalog\\n184 addressed"] --> shared["Hermes shared skills\\n64 converted now"]',
        '  native["Existing Hermes skills\\nprofile + shared + platform"] --> arsenal["Skill arsenal"]',
        '  shared --> arsenal',
        '  arsenal --> atlas["Atlas CEO\\nexecutive decisions"]',
        '  arsenal --> marin["Marin\\nrevenue + marketing"]',
        '  arsenal --> quill["Quill\\ndrafting + creative"]',
        '  arsenal --> stet["Stet\\ncritique + evidence"]',
        '  arsenal -. parked .-> techop["Future technical-operator\\nengineering governance"]',
        "```",
        "",
        "## Active Arsenal Counts",
        "",
        "| Source | Count |",
        "| --- | ---: |",
    ]
    for source, count in sorted(source_counts.items()):
        lines.append(f"| {source} | {count} |")
    lines.extend(["", "| Owner | Count |", "| --- | ---: |"])
    for owner, count in sorted(owner_counts.items()):
        lines.append(f"| {markdown_cell(owner)} | {count} |")

    lines.extend(
        [
            "",
            "## Every Active Skill",
            "",
            "| Skill | Owner | Source | Kind | Fit | Status | Path |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for skill in active:
        lines.append(
            f"| `{markdown_cell(skill.name)}` | {markdown_cell(skill.owner)} | {skill.source} | "
            f"{markdown_cell(skill.kind)} | {markdown_cell(skill.fit)} | {skill.status} | `{skill.path}` |"
        )

    lines.extend(
        [
            "",
            "## Every Agency Catalog Skill Addressed",
            "",
            "| Source Skill | Recommended Owner | Fit | Priority | Status | Boundary |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in items:
        boundary = "keep out of profiles" if item.status == "blocked-role-boundary" else item.bucket
        lines.append(
            f"| `{item.relpath}` | {markdown_cell(recommended_owner_for_item(item))} | "
            f"{markdown_cell(fit_for_agency_item(item))} | {item.priority} | {item.status} | {boundary} |"
        )

    lines.extend(
        [
            "",
            "## Reading The Map",
            "",
            "- `Owner` means the profile that should reach for the skill first.",
            "- `Shared` means the skill can be used by multiple profiles but should still be invoked through the owning profile's boundaries.",
            "- `Deferred` means it is intentionally visible but not installed until a real project asks for it.",
            "- `Blocked` means it would blur the profile-vs-skill boundary and should stay out of the skill arsenal.",
            "",
        ]
    )
    ARSENAL_MAP_MD.write_text("\n".join(lines), encoding="utf-8")


def all_converted_agency_skills(items: list[AgencyItem]) -> set[str]:
    return {item.slug for item in items if item.status.startswith("converted")}


def update_manifest(profile: str, skills: list[str], agency_skills: set[str]) -> None:
    path = REPO_ROOT / f"hermes/profiles/{profile}/manifest.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    existing = data.get("skills", [])
    existing = [skill for skill in existing if skill not in agency_skills]
    for skill in skills:
        if skill not in existing:
            existing.append(skill)
    data["skills"] = existing
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def remove_profile_note(profile: str) -> None:
    path = REPO_ROOT / f"hermes/profiles/{profile}/CLAUDE.md"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    marker = "## Shared Agency Skills"
    if marker not in text:
        return
    text = re.sub(
        rf"\n{re.escape(marker)}\n.*?(?=\n## |\Z)",
        "\n",
        text,
        flags=re.S,
    ).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def append_profile_notes() -> None:
    for profile in DISABLED_PROFILE_NOTES:
        remove_profile_note(profile)
    for profile, skills in PROFILE_ENABLEMENT.items():
        path = REPO_ROOT / f"hermes/profiles/{profile}/CLAUDE.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        marker = "## Shared Agency Skills"
        block = [
            "",
            marker,
            "",
            "This profile may use the following Agency-derived shared skills from `hermes/shared-skills/agency/`. They are procedural workflows only: they do not create new profiles, dispatch subagents, publish, send, spend, or run unattended automation.",
            "",
            ", ".join(f"`{skill}`" for skill in skills),
            "",
        ]
        if marker in text:
            text = re.sub(
                rf"\n{re.escape(marker)}\n.*?(?=\n## |\Z)",
                "\n" + "\n".join(block).strip() + "\n",
                text,
                flags=re.S,
            )
        else:
            text = text.rstrip() + "\n" + "\n".join(block)
        path.write_text(text, encoding="utf-8")


def write_artifact(items: list[AgencyItem], upstream_commit: str) -> None:
    ARTIFACT_MD.parent.mkdir(parents=True, exist_ok=True)
    converted = [i for i in items if i.status.startswith("converted")]
    active = discover_active_arsenal(items)
    owner_counts: dict[str, int] = {}
    for skill in active:
        owner_counts[skill.owner] = owner_counts.get(skill.owner, 0) + 1
    lines = [
        "# Agency Skills Conversion - 2026-05-20",
        "",
        "## Snapshot",
        "",
        f"- Source repo: `msitarzewski/agency-agents`",
        f"- Source commit: `{upstream_commit}`",
        f"- Upstream agent files classified: {len(items)}",
        f"- Converted now: {len(converted)}",
        f"- Active skill arsenal mapped: {len(active)}",
        "- Canonical skill home: `/Users/alexhale/Projects/agents/hermes/shared-skills/agency/`",
        "- Owner map: `/Users/alexhale/Projects/agents/hermes/shared-skills/agency/ARSENAL-MAP.md`",
        "",
        "## Conversion Flow",
        "",
        "```mermaid",
        "flowchart LR",
        '  A["Agency markdown agents"] --> B["Classify 184 files"]',
        '  B --> C["Convert P1 + curated high-stakes"]',
        '  C --> D["Hermes shared skills"]',
        '  D --> E["Profiles opt in deliberately"]',
        '  E --> F["Validator + trigger matrix"]',
        "```",
        "",
        "## Ownership Overview",
        "",
        "| Owner | Active skills mapped | Primary fit |",
        "| --- | ---: | --- |",
    ]
    for owner, count in sorted(owner_counts.items()):
        fit = next((PROFILE_FIT[k] for k, label in PROFILE_LABELS.items() if label == owner), "")
        lines.append(f"| {markdown_cell(owner)} | {count} | {markdown_cell(fit)} |")
    lines.extend(
        [
            "",
        "## Profile Enablement",
        "",
        "| Profile | Enabled shared Agency skills |",
        "| --- | --- |",
        ]
    )
    for profile, skills in PROFILE_ENABLEMENT.items():
        lines.append(f"| `{profile}` | " + ", ".join(f"`{s}`" for s in skills) + " |")
    lines.extend(["", "## Parked Candidates", "", "| Bucket | Skills |", "| --- | --- |"])
    for bucket, skills in PARKED_CANDIDATES.items():
        lines.append(f"| {markdown_cell(PARKED_LABELS[bucket])} | " + ", ".join(f"`{s}`" for s in skills) + " |")
    lines.extend(
        [
            "",
            "## Every Active Skill In The Arsenal",
            "",
            "| Skill | Owner | Source | Fit | Status |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for skill in active:
        lines.append(
            f"| `{markdown_cell(skill.name)}` | {markdown_cell(skill.owner)} | {skill.source} | "
            f"{markdown_cell(skill.fit)} | {skill.status} |"
        )
    lines.extend(
        [
            "",
            "## Full Classification Matrix",
            "",
            "| Division | Source | Skill | Owner | Fit | Priority | Bucket | Status | Reason |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in items:
        skill = item.slug if item.status.startswith("converted") else ""
        lines.append(
            f"| {item.division} | `{item.relpath}` | `{skill}` | "
            f"{markdown_cell(recommended_owner_for_item(item))} | {markdown_cell(fit_for_agency_item(item))} | "
            f"{item.priority} | {item.bucket} | {item.status} | {markdown_cell(item.reason)} |"
        )
    lines.extend(
        [
            "",
            "## Next 1% Move",
            "",
            "Run one real Marin AEO/citation request through `marketing-ai-citation-strategist`, then have Stet review the memo with `testing-reality-checker` before promoting the workflow into a recurring marketing operating packet.",
            "",
        ]
    )
    ARTIFACT_MD.write_text("\n".join(lines), encoding="utf-8")
    if HTML_RENDERER.exists():
        subprocess.run(["python3", str(HTML_RENDERER), str(ARTIFACT_MD)], check=True)


def main() -> None:
    upstream_commit = ensure_upstream()
    items = discover_items(upstream_commit)
    AGENCY_ROOT.mkdir(parents=True, exist_ok=True)
    for child in AGENCY_ROOT.iterdir():
        if child.is_dir() and (child / "SKILL.md").exists():
            shutil.rmtree(child)
    for item in items:
        if item.status.startswith("converted"):
            write_skill(item, upstream_commit)
    write_catalog(items, upstream_commit)
    write_arsenal_map(items, upstream_commit)
    agency_skills = all_converted_agency_skills(items)
    for profile, skills in PROFILE_ENABLEMENT.items():
        update_manifest(profile, skills, agency_skills)
    for profile in DISABLED_PROFILE_NOTES:
        update_manifest(profile, [], agency_skills)
    append_profile_notes()
    write_artifact(items, upstream_commit)
    print(
        f"Built {len([i for i in items if i.status.startswith('converted')])} skills "
        f"from {len(items)} Agency files at {upstream_commit}"
    )


if __name__ == "__main__":
    main()
