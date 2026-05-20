---
name: campaign-brief-draft
description: Draft a campaign brief tied to one offer, one audience, one source, one metric. Mirrors the AI Ops Audit campaign brief shape.
input: campaign name + intended offer + intended audience
output: markdown to ~/Projects/marketing/_inbox/marin-readouts/{YYYY-MM-DD}-brief-{slug}.md
---

# Skill: campaign-brief-draft

## Purpose

Draft a campaign brief that ties one offer to one audience with one front-door asset and one primary metric. The shape mirrors `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/campaign-brief.md` — that's the gold-standard reference.

## Inputs (must read before drafting)

1. `~/Projects/marketing/brand/prettyfly-company-truth.md`
2. `~/Projects/marketing/offers/revenue-ladder.md`
3. `~/Projects/marketing/offers/<offer>.md` (the specific offer this brief targets)
4. `~/Projects/marketing/research/prettyfly-cto-advisory-icp.md` (or the relevant ICP research)
5. `~/Projects/marketing/content/content-pillars.md`
6. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md`
7. AI Ops Audit reference brief: `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/campaign-brief.md`
8. `MEMORY.md`

## Required brief sections

Follow the AI Ops Audit brief structure exactly:

1. **Campaign** — single sentence positioning the campaign inside the revenue ladder
2. **Target** — concrete audience: employee count band, revenue band, vertical, geography, SaaS-tool count, AI-team status, pain heuristic
3. **Pain** — one paragraph naming the specific buyer pain, NOT generic "they need AI"
4. **Offer** — what the audit/sprint/audit actually delivers, what it leads into next on the ladder
5. **Front Door** — the lowest-friction asset (Scorecard, WORKS Review, Field Note)
6. **Why Now** — one paragraph naming the market force or buyer condition that makes this campaign timely
7. **Proof To Use** — list of concrete artifacts (PrettyFly company truth statements, workflow teardowns, scorecard outputs, before/after examples)
8. **Primary Metric** — ONE metric (e.g. "booked qualified diagnostic calls with advisory potential")
9. **Continue Criteria** — what signals say "keep running"
10. **Pivot Criteria** — what signals say "adjust audience or message"

## Anti-patterns to avoid

- Multi-offer briefs (each brief = ONE offer)
- Multi-audience briefs (each brief = ONE audience)
- Multiple primary metrics (forces dilution)
- Inventing market conditions, deal sizes, or competitor names
- Including channels that violate the kill list (D2C, $500 website on premium channels, etc.)
- Hype copy in the Pain or Why Now sections — those should sound like an operator's diagnosis, not ad copy
- Including any "Pivot Criteria" that lets the campaign keep running indefinitely without buyer signal

## Source citation rule

Every claim about audience, pain, offer mechanics, or proof must cite a vault file or be explicitly labeled `assumption (not yet sourced)`. Assumptions are allowed but must be flagged so Alex can validate before launch.

## Output destination

`~/Projects/marketing/_inbox/marin-readouts/{YYYY-MM-DD}-brief-{campaign-slug}.md`

Never write to `campaigns/<campaign-slug>/campaign-brief.md` directly — Alex promotes from inbox to active campaign folder.
