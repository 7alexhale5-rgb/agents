---
date: 2026-05-30
type: decision
project: agents
tags: [adr, hermes, profiles, sentinel, seo, aeo, marketing, rung-1, propose-only, yagni, sine]
status: accepted
related_adrs:
  - 2026-05-18-subproject-to-profile-trigger.md
  - 2026-05-18-agent-shape-11-file-contract.md
  - 2026-05-20-capability-build-sequence.md
---

# ADR: Add `sentinel` as a Propose-Only SEO/AEO Execution Profile

## Decision

Add `hermes/profiles/sentinel/` as a rung-1, propose-only SEO/AEO execution profile targeting prettyflyforai.com. All outputs are proposals dropped to `_inbox/sentinel-drafts/`; no live publishing, no CMS or DNS mutations.

| Surface         | Setting                                                                                                      |
| --------------- | ------------------------------------------------------------------------------------------------------------ |
| Rung            | **1** (propose-only)                                                                                         |
| Authority       | read-only on site + search data; propose-only writes to `_inbox/sentinel-drafts/`                           |
| Department      | marketing                                                                                                    |
| Channels        | CLI + inbox files only; no Slack, no email, no Telegram at launch                                           |
| Scope           | SEO/AEO execution only; social content parked                                                                |
| Spend cap       | $0/day autonomous spend; model API cost rolls up to the global fleet ledger                                  |
| Acceptance gate | Dry-run: one SEO audit + one metadata pack + one AEO brief land in `_inbox/sentinel-drafts/` without errors |
| Promotion path  | Rung 2+ requires a separate ADR after the dry-run acceptance gate passes                                     |

## Context

Two prior profiles addressed adjacent SEO/AEO territory but neither owns execution:

- **Polsia** (historical) carried a task catalog covering SEO audits, metadata packs, schema packs, AEO content briefs, competitor-citation teardowns, and opportunity scoring. Polsia's patterns and task catalog are absorbed verbatim here.
- **Sentinel v1** (historical) established the name and a propose-only execution posture. This ADR formalizes that posture inside the current fleet contract.

The current fleet has a clear marketing lane gap: Marin sets campaign strategy; Quill drafts approved copy; no profile owns the search-specific execution layer (crawl analysis, structured-data proposals, AEO brief construction, competitor citation work). prettyflyforai.com has measurable organic search opportunity that is currently unserved by any live profile.

## Department Boundary: Marin / Sentinel / Quill

| Profile    | Owns                                                                  | Does NOT own                                         |
| ---------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| `marin`    | Strategy, ICP, campaign direction, topic approval                     | Execution artifacts, schema markup, audit triage     |
| `sentinel` | SEO/AEO execution — audits, metadata/schema, briefs, teardowns        | Strategy decisions, social content, copy finalization |
| `quill`    | Copy drafting from approved briefs (including sentinel AEO briefs)    | SEO technical audits, structured data, search intent |

Sentinel's inputs come from Marin (approved topics, campaign direction) and raw site/search data. Sentinel's outputs feed Quill (AEO briefs become Quill inputs) and Alex directly (audits, schema proposals, teardowns).

## Why This Profile Clears the Three-Test Bar

A capability earns profile status only when it has (a) persona-distinct voice, (b) long-running state, (c) channel-isolated identity:

- **Persona-distinct voice:** SEO/AEO execution requires a different mode than Marin's strategic framing or Quill's brand-voice copy — it is technical, source-cited, structured-data-native, and search-intent-first.
- **Long-running state:** Audit snapshots, keyword baselines, schema change history, and competitor citation inventories must persist across sessions to track drift and measure movement.
- **Channel-isolated identity:** `_inbox/sentinel-drafts/` is a distinct artifact surface; no other profile should write audit reports or schema proposals there.

## Task Catalog (from Polsia + Sentinel v1)

- Site-wide SEO audit (crawl + Core Web Vitals + structural findings)
- Metadata packs (title + description, per-page, keyword-aware)
- JSON-LD schema packs (structured data proposals, schema.org-compliant)
- AEO content briefs (answer-engine optimization; question-cluster + source-citation structure)
- Competitor-citation teardowns (who ranks for target queries; what content patterns they use)
- Opportunity scoring (query volume × difficulty × fit × current rank gap)

## Consequences

1. **Dry-run acceptance gate (before rung 2 can be requested):** sentinel must produce one SEO audit + one metadata pack + one AEO brief for prettyflyforai.com landing in `_inbox/sentinel-drafts/` without hallucinating data. Alex reviews and confirms findings are actionable before any promotion path opens.
2. **Social content remains parked.** Social execution stays with Quill. Sentinel does not acquire social scheduling, drafting, or channel-management tasks.
3. **No direct CMS or DNS authority, ever, at rung 1.** Schema proposals are JSON files to be applied by a human operator. Metadata packs are markdown/CSV; not pushed to any live system.
4. **Marin upstream dependency is explicit.** Sentinel does not set its own topic agenda; approved topics come from Marin. If Marin is not yet running (Phase 2 still in pilot), Alex provides topic direction directly.
5. **Reversibility:** TYPE-2. `rm -rf hermes/profiles/sentinel/` and revert this ADR undoes the slice in under a minute. Inbox drafts are operator artifacts, not system state.

## What This Slice Does NOT Do

- Promote sentinel past rung 1.
- Wire any live publishing surface (no Webflow, no Ghost, no Contentful).
- Grant link-building outreach authority (viper-outreach lane).
- Add paid search / SEM tasks.
- Touch Marin, Quill, or any other profile.

## 1% Engineer Move

After the dry-run gate passes: fire one SEO audit against prettyflyforai.com, capture the artifact in `_inbox/sentinel-drafts/`, and let Alex confirm one finding is actionable before writing the rung-2 promotion ADR.
