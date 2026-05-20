# Agent Role Skill Ownership Cleanup Plan

Date: 2026-05-20  
Mode: planning-stack --deep, tech/architecture  
Goal: Attach Agency-derived skills to the right Hermes roles without reintroducing the `codex` profile mistake or bloating the fleet.

## Context

The company goal is PrettyFly CTO Advisory to `$1M ARR` in 24 months. The Hermes fleet should only carry roles and skills that unlock revenue creation, delivery, retention, reliability, or executive leverage.

Recent ADR locks the key rule: `Codex` is the OpenAI tool/runtime lane, not a Hermes profile. The future technical governance role is `technical-operator` / `CTO`, but it has not earned profile status yet.

The current dirty Agency consolidation attaches 64 converted shared skills across Atlas, Codex, Marin, Quill, and Stet. That needs one cleanup pass before commit.

## Architecture Decision

Use three skill states instead of forcing every converted skill into an active profile:

| State | Meaning | Commit posture |
| --- | --- | --- |
| Active profile opt-in | Skill is directly useful to a current Hermes profile and fits its authority. | Add to that profile docs/manifests. |
| Parked candidate | Skill is valid, converted, and may be useful later, but no current profile should own it yet. | Keep in shared catalog; do not enable in profile manifest. |
| Deferred/reference | Skill is not relevant to the `$1M ARR` path or needs a live client/project trigger. | Keep cataloged only. |

This preserves speed without pretending the org is larger than it is.

## Role Map

| Role | Hermes status | Active skill posture |
| --- | --- | --- |
| Alex CEO | Human owner | No Hermes skills. Uses Codex/Claude/Cursor as tools. |
| `atlas-ceo` | Active Hermes profile | Executive signal, decision support, product/revenue prioritization, high-stakes advisory only. |
| `marin` | Active Hermes profile | Marketing/revenue-loop strategy, buyer signal routing, AEO/GEO, LinkedIn/sales motion. |
| `quill` | Active Hermes profile | Drafting and creative production from approved positioning only. |
| `stet` | Active Hermes profile | Pre-launch critique, claim QA, evidence/test review. |
| VanClief COO | Future process/profile | No active Agency skills yet. Candidate home for project-management/support ops skills after a cadence trigger. |
| CTO / `technical-operator` | Future profile, human technical operator now | Engineering/testing skills stay parked until the profile earns identity. |
| `koho-ops`, `yeh-ops` | Future retainer delivery profiles | No Agency opt-ins until paid delivery load exists. |
| `codex` | Not a fleet identity | Remove active profile enablement. Codex remains tool/runtime lane only. |

## Skill Attachment Plan

### `atlas-ceo` active

Keep as procedural decision-support skills:

- `product-behavioral-nudge-engine`
- `product-feedback-synthesizer`
- `product-manager`
- `product-sprint-prioritizer`
- `product-trend-researcher`
- `sales-pipeline-analyst`
- `specialized-compliance-auditor`
- `finance-tax-strategist`

Boundary: Atlas may use these to advise and propose. It must not become PM, CFO, compliance officer, or daily ops dispatcher.

### `marin` active, reduced to current revenue loop

Keep:

- `marketing-agentic-search-optimizer`
- `marketing-ai-citation-strategist`
- `marketing-linkedin-content-creator`
- `marketing-seo-specialist`
- `sales-account-strategist`
- `sales-coach`
- `sales-deal-strategist`
- `sales-discovery-coach`
- `sales-engineer`
- `sales-outbound-strategist`
- `sales-pipeline-analyst`
- `sales-proposal-strategist`

Park until channel/tool trigger:

- `marketing-reddit-community-builder`
- `marketing-social-media-strategist`
- `marketing-twitter-engager`
- all `paid-media-*`

Boundary: Marin decides the revenue loop and proposes. It does not publish, spend, send, or run paid media.

### `quill` active, reduced to content/draft production

Keep:

- `design-brand-guardian`
- `design-image-prompt-engineer`
- `design-inclusive-visuals-specialist`
- `design-visual-storyteller`
- `marketing-content-creator`
- `marketing-linkedin-content-creator`

Park until specific artifact trigger:

- `design-ui-designer`
- `design-ux-architect`
- `design-ux-researcher`
- `design-whimsy-injector`
- `marketing-podcast-strategist`

Boundary: Quill drafts. It does not become a design department, publisher, or product designer.

### `stet` active

Keep:

- `design-brand-guardian`
- `specialized-compliance-auditor`
- `testing-accessibility-auditor`
- `testing-evidence-collector`
- `testing-performance-benchmarker`
- `testing-reality-checker`
- `testing-test-results-analyzer`
- `testing-tool-evaluator`

Boundary: Stet critiques and verifies artifacts. It does not rewrite, publish, deploy, or own engineering.

### CTO / `technical-operator` parked candidates

Park all converted engineering/testing skills currently mapped to `codex`:

- `engineering-*`
- `specialized-automation-governance-architect`
- `specialized-lsp-index-engineer`
- `specialized-mcp-builder`
- `specialized-model-qa`
- `testing-api-tester`
- `testing-workflow-optimizer`

Shared testing skills that Stet can use stay active for Stet, but the engineering ownership side is parked.

Boundary: no `technical-operator` profile until earned by recurring technical governance load.

### VanClief COO parked candidates

Do not convert or enable yet. Future candidates, if a COO cadence trigger fires:

- project-management catalog items
- support/infrastructure/support-reporting catalog items
- operations/cadence checklists created from real repeated work

Boundary: VanClief COO should track cadence and pressure-test execution, not become a generic staff profile.

## Files To Modify

| File | Change |
| --- | --- |
| `scripts/build-agency-shared-skills.py` | Replace `codex` enablement with parked `technical-operator` candidates; reduce active Marin/Quill skill lists; make labels say parked where not profile-enabled. |
| `hermes/shared-skills/agency/catalog.json` | Regenerate from script. |
| `hermes/shared-skills/agency/CATALOG.md` | Regenerate from script. |
| `hermes/shared-skills/agency/ARSENAL-MAP.md` | Regenerate from script with no active Codex owner. |
| `hermes/shared-skills/agency/TRIGGER-MATRIX.md` | Regenerate if script touches it. |
| `hermes/profiles/marin/CLAUDE.md` and `manifest.json` | Remove parked channel/paid-media opt-ins. |
| `hermes/profiles/quill/CLAUDE.md` and `manifest.json` | Remove parked UI/UX/podcast/whimsy opt-ins. |
| `hermes/profiles/codex/CLAUDE.md`, `manifest.json`, `DOCTRINE.md` | Remove Agency opt-ins and unbless the generated doctrine. Keep `codex` as placeholder/runtime-lane artifact only if still needed by legacy lint. |
| `hermes/profiles/codex/skills/.gitkeep` | Restore tracked placeholder or replace with a tracked README only if lint requires it. |
| `hermes/shared-skills/README.md` | Update summary language if it currently names Codex as owner. |

## Implementation Steps

1. Patch the Agency build script ownership constants.
2. Regenerate Agency shared skill docs/catalog from the script.
3. Patch active profile docs/manifests to match the reduced active opt-ins.
4. Remove the dirty Codex profile skill opt-ins and untracked Codex doctrine file.
5. Restore the `codex/skills` tracked placeholder so profile lint is stable.
6. Run validation.

## Test Plan

- `python3 scripts/validate-agency-skills.py`
- `scripts/lint-profile.sh atlas-ceo codex marin quill stet`
- `scripts/validate-profile.sh atlas-ceo`
- `scripts/validate-profile.sh marin`
- `scripts/validate-profile.sh quill`
- `scripts/validate-profile.sh stet`
- JSON parse every touched `manifest.json`
- `git diff --check`
- `rg -n "Owner.*Codex|Profile Enablement.*codex|profile: codex|agent_id: codex" hermes/shared-skills/agency hermes/profiles/codex _meta/decisions`

## Risks

| Risk | Severity | Mitigation |
| --- | --- | --- |
| Over-pruning useful marketing/design skills | Medium | Park, do not delete. Re-enable when a route/channel trigger fires. |
| Breaking generated docs consistency | Medium | Patch generator first, then regenerate. |
| Accidentally deleting user-owned dirty work | Medium | Only touch agency/codex collision files named in this plan. |
| Lint expects `codex/skills` path | Low | Restore tracked placeholder. |

## Reversibility Ledger

| Step | Class | Cost if wrong | Recommendation |
| --- | --- | --- | --- |
| Remove Codex profile enablement | Type 2 | Low; can re-add later under a new ADR | Fast-track |
| Park paid-media/social/UI/UX skills | Type 2 | Low; skills remain on disk | Fast-track |
| Patch generator ownership model | Type 2 | Low; generated docs can be rerun | Fast-track |
| Delete untracked Codex doctrine | Type 2 | Low; invalid under ADR | Safe after diff review |

## Acceptance Criteria

- No active shared-skill docs or generated catalogs name Codex as a profile owner.
- Active profile manifests only include skills aligned with current authority and `$1M ARR` path.
- Engineering/testing skills are parked as future `technical-operator` candidates, not attached to a live profile.
- Existing active profiles pass lint/validation.
- Dirty worktree is reduced to intentional Agency consolidation files plus any unrelated user-owned files.

## Planning Stack Report

- Mode: TECH
- Depth: --deep
- Confidence: High for ownership policy, medium-high for exact active/park split
- Sources: repo ADRs, profile manifests/docs, Agency catalog/docs, build/validation scripts
- Memory: strict wiki failed; repo ADRs used as source of truth
- Research: skipped; no external unknowns
- Prior decisions applied: 2026-05-18 agent shape contract, 2026-05-18 subproject trigger, 2026-05-20 Codex/tool ADR

## 1% Engineer Move

Next best target: implement the ownership cleanup in the generator and profile manifests, starting with removing active Codex enablement.

Why it beats alternatives: it prevents the current dirty consolidation from committing a wrong fleet identity.

Expected confidence: high. Most changes are generated docs and manifest/docs alignment.

Should wait: creating `technical-operator`, adding VanClief COO, enabling paid media, creating Koho/Yeh retainer skills, and any autonomous technical execution authority.
