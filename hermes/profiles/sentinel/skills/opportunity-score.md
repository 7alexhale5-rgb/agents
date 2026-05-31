---
name: opportunity-score
description: ROI-score a list of AEO/SEO opportunities for prettyflyforai.com so Marin can prioritize them in a decision memo. Produces one ranked impact/effort matrix written to the sentinel-drafts inbox. Propose-only — never deploys, edits the live site, or opens a PR.
input: a gap queue (list of opportunity slugs or a prior audit artifact path); optionally a GSC data export path or inline position/impression data
output: markdown to ~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-opportunity-score-{slug}.md + Hermes local receipt
---

# Skill: opportunity-score

## Purpose

Score and rank a queue of AEO/SEO opportunities for prettyflyforai.com so Marin can make a data-backed prioritization decision in her weekly memo. Every opportunity gets a falsifiable ROI score (impact × effort inverse), a tier assignment, a first action, and a measurement plan tied to GSC + GA4 AI-referral.

The output is a paste-ready decision input — not a deployment artifact. Alex or Marin deploys nothing from this skill output without a separate verify-then-deploy pass.

Success metric: Marin can read the output, pick the top-3 opportunities, and write a one-paragraph prioritization rationale that cites observable GSC or GA4 data — not estimates.

## Inputs (must read in this order before scoring)

1. `MEMORY.md` — current audit gap record and HIGH-risk flags; the gap queue lives here unless the caller supplies an override list
2. `DOCTRINE.md` — decision rules, banned tactics, measurement doctrine, canonical source anchors; all scoring judgments must be consistent with this
3. `USER.md` — prettyflyforai.com positioning and ICP; used to calibrate intent-match scoring
4. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts, active offers, proof points; used to judge whether an opportunity is on-brand and executable
5. `~/Projects/marketing/brand/voice-and-anti-slop.md` — voice spine; used when writing opportunity descriptions in the output
6. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md` — confirm no opportunity depends on a paid tool that has not cleared its trigger condition
7. GSC/GA4 data (caller-supplied or noted as "not available"): current position, impressions, click-through rate, AI-referral session count per opportunity; if not supplied, mark each field `gsc:unavailable` and score on structural signals only

## Procedure

1. **Load the gap queue.** Read `MEMORY.md` boot anchors for the current gap list. If the caller supplied an explicit list or a prior audit artifact path (e.g. `_inbox/sentinel-drafts/{date}-aeo-technical-audit-{slug}.md`), use that instead. De-duplicate by opportunity slug. Reject any opportunity not grounded in a documented gap — do not invent gaps.

2. **For each opportunity, collect the five scoring inputs:**
   - **GSC position** (integer 1–50, or `null` if not ranking): closer to position 1 = lower positional delta, less opportunity for quick win; positions 11–20 (page 2) score highest for push-tier ROI.
   - **GSC impressions / AI-referral sessions** (absolute count from caller-supplied data, or `gsc:unavailable`): higher = higher demand signal.
   - **Intent match** (classify the target query using the three-tier schema from `intelligence.js § scoreIntent`): `high` (hire/cost/price/quote/near-me intent) = 2.0×; `medium` (best/top/review/compare) = 1.5×; `service-specific` (audit/advisory/AI ops) = 1.3×; `generic` = 1.0×. Cite the query or page title that informs the classification.
   - **Implementation effort** (classify as `low` / `medium` / `high`): `low` = metadata-only or schema addition, no copy change; `medium` = answer-first content block + schema, one page; `high` = new page, full content cluster, or entity-consistency work across multiple properties. Cite what work is required.
   - **AEO structural readiness** (classify as `ready` / `partial` / `missing`): does the target page already have question-shaped H2s, a 40-60 word extractable answer block, FAQPage or HowTo JSON-LD, and entity/sameAs consistency? Score `ready` = 0 additional AEO lift needed; `partial` = one or two elements missing; `missing` = no AEO structure present.

3. **Compute the ROI score for each opportunity.** Use this formula (adapted from `intelligence.js § scoreOpportunities`):

   ```
   positionScore  = max(0, 50 - position)          # null position = 0
   page2Bonus     = 2.0 if position 11–20 else 1.0
   intentScore    = 2.0 | 1.5 | 1.3 | 1.0          # from step 2
   effortPenalty  = 1.0 | 0.7 | 0.4                # low=1.0, medium=0.7, high=0.4
   aeoBonus       = 1.0 | 1.3 | 1.6                # ready=1.0, partial=1.3, missing=1.6

   opportunityScore = round(positionScore × page2Bonus × intentScore × effortPenalty × aeoBonus)
   ```

   If GSC position is `null` (no ranking page exists), apply a flat base score of 5 before multipliers (the page must be created, which is medium-to-high effort by definition). If all GSC data is `gsc:unavailable`, note that scores are structural-signal-only and flag the output as `confidence: low` in the frontmatter.

4. **Assign a tier to each opportunity:**
   - `push` — position 11–20, opportunityScore ≥ 30: quick-win candidates for this sprint.
   - `build` — position 21–50, or no page: medium-term content/entity work.
   - `defend` — position 1–3: monitor only; do not over-optimize.
   - `maintain` — position 4–10: minor incremental work; not sprint priority.
   - `aeo-structure` — position is any but aeoReadiness = `missing` and intentScore ≥ 1.3: AEO structural gap that elevates citation probability regardless of ranking position.

5. **Write the first action for each opportunity.** Match the tier to an action string:
   - `push` — "Add answer-first content block + FAQPage JSON-LD. Verify in GSC rich-result tester after deploy."
   - `build` — "Create page or expand existing to ≥800 words. Add HowTo or Article JSON-LD. Build one supporting internal link."
   - `defend` — "Monitor GSC position weekly. Refresh content only if impressions drop >20% month-over-month."
   - `maintain` — "Add one internal link from a high-traffic page. Check entity sameAs consistency."
   - `aeo-structure` — "Add question-shaped H2 + 40-60 word extractable answer block. Add FAQPage JSON-LD. Measure AI-referral sessions in GA4 before/after."

6. **Build the ranked table.** Sort all opportunities descending by `opportunityScore`. Group into sections by tier (`push` first, then `aeo-structure`, then `build`, `maintain`, `defend`). Within each tier, sort descending by score.

7. **Write the measurement plan.** For every opportunity in the `push` and `aeo-structure` tiers, append a three-line measurement plan:
   - GSC check: what signal to look for in Search Console (rich-result eligibility, impressions delta, position delta) and a timeframe (typically 2–4 weeks post-deploy for schema; 4–8 weeks for content changes).
   - GA4 AI-referral check: confirm the AI-referral channel group is tracking sessions from ChatGPT/Perplexity/AI Overview click-through. Note baseline session count if available from caller-supplied data.
   - Pass condition: "Opportunity closes when GSC impressions for this query increase ≥10% and/or AI-referral sessions attributable to this page increase by ≥1 per week over a 4-week rolling window." Adjust thresholds if caller-supplied data provides a tighter baseline.

8. **Source-ground every claim in the output.** Each opportunity description must cite at least one of: `MEMORY.md` (gap reference), caller-supplied GSC data, a `DOCTRINE.md` canonical source anchor (arXiv 2605.14021, 2604.27790, 2603.29979, or Google Search Central AI features URL), or a marketing vault file path. No invented metrics. If a claim cannot be grounded, delete it and note `[source: not available]`.

9. **Check against banned tactics.** Before writing, confirm no recommended action includes: llms.txt as a citation lever, "magic schema" ranking promises, autonomous site edits, keyword-stuffed JSON-LD, new paid SEO tooling without a cleared trigger. Reject and rewrite any line that violates `DOCTRINE.md § Banned tactics`.

10. **Run the no-side-effects gate** (see Validation below).

11. **Write the artifact** to `~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-opportunity-score-{slug}.md` where `{slug}` is a 2-4 word kebab-case descriptor of the gap queue (e.g. `homepage-aeo-gaps`, `q2-sprint-queue`). Use the frontmatter from `DOCTRINE.md § Output contract` with `skill: opportunity-score`, `audit_gap:` set to the primary gap driving the queue (or `"queue-{n}-items"` if multiple), `impact:` and `effort:` set to the top-tier opportunity's values.

12. **Emit the Hermes local receipt.** Call `artifact.propose` to write the receipt with `type=sentinel.draft.proposed`, `status=pending`, `surface=cli`, `cwd_project=marketing`, `skill_slug=opportunity-score`, `data.runtime=hermes`, `data.proposal_status=proposed`, `data.private_payload_redacted=true`. The receipt may include artifact type, impact, effort, top-tier opportunity count, confidence level, and vault-relative draft path. It must not include raw page source, scraped HTML, or full GSC data tables.

## Output shape

```markdown
---
date: {YYYY-MM-DD}
type: sentinel-draft
status: proposed
project: prettyflyforai-seo-aeo
skill: opportunity-score
agent: sentinel
site: prettyflyforai.com
audit_gap: {gap name or "queue-N-items"}
impact: {high | medium | low}
effort: {high | medium | low}
confidence: {high | low}           # low = gsc:unavailable, structural-signal-only
verify_after_deploy: "Check GSC rich-result status and AI-referral channel in GA4"
private_payload_redacted: true
---

# AEO/SEO Opportunity Score — {slug}
**Date:** {YYYY-MM-DD} | **Site:** prettyflyforai.com | **Queue size:** {N}

## Decision input for Marin
> {1-2 sentence summary of the top-3 opportunities and the recommended sprint focus.
>  Plain English. Cite at least one GSC or AEO structural signal.}

## Ranked opportunity table

| # | Opportunity | Tier | Score | Position | Intent | Effort | AEO Readiness | Source |
|---|-------------|------|-------|----------|--------|--------|---------------|--------|
| 1 | {name} | push | {score} | {pos} | {intent} | {effort} | {readiness} | {vault file or GSC} |
...

## Push-tier details (sprint candidates)

### {Opportunity name}
- **Gap:** {one-line description citing MEMORY.md or audit artifact}
- **First action:** {verbatim action string from step 5}
- **Measurement plan:**
  - GSC: {what to check, timeframe}
  - GA4 AI-referral: {baseline sessions if known, what increase to look for}
  - Pass condition: {threshold — see step 7}
- **Source:** {MEMORY.md § {section} | arXiv {id} | GSC data supplied by caller}

[repeat for each push-tier opportunity]

## AEO-structure gaps (citation-risk, any position)

[same format as push-tier details]

## Build / maintain / defend queue (not this sprint)

| Opportunity | Tier | Score | Next review |
|-------------|------|-------|-------------|
...

## Verification step (after Alex deploys any push-tier fix)
1. Run the artifact's specific schema type through schema.org/validator or Google's Rich Results Test.
2. Check GSC > Search results > filter to the target query; confirm impressions trend within 2–4 weeks.
3. Check GA4 > Acquisition > channel group "AI Referral" for sessions from the target page; note baseline before deploy.
4. If impressions or AI-referral sessions do not move within the pass-condition window, escalate to Marin for strategy review — do not re-optimize without a fresh gap diagnosis.
```

## Validation checklist

Before emitting the Hermes receipt, confirm ALL of the following:

- [ ] Every opportunity in the output traces to a documented gap in `MEMORY.md` or a caller-supplied audit artifact — no invented gaps.
- [ ] Every score is computed from the formula in step 3 with explicit input values shown in the table — no black-box numbers.
- [ ] Every claim in the opportunity descriptions cites a source (vault file, GSC data, or canonical arXiv/Google anchor) — no ungrounded assertions.
- [ ] No banned tactic appears in any first-action or recommendation (llms.txt as citation lever, magic schema, autonomous deploy, keyword-stuffed JSON-LD, new paid tooling without trigger).
- [ ] The measurement plan for every push-tier and aeo-structure opportunity names an observable GSC or GA4 signal with a falsifiable pass condition.
- [ ] `confidence:` is set to `low` if GSC data was unavailable; `high` only if caller-supplied position/impressions data was used for at least 50% of scored opportunities.
- [ ] The artifact file is written to `~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-opportunity-score-{slug}.md` — nowhere else.

## No external side-effects gate (hard stop)

**This skill produces exactly one deliverable: the scored opportunity document in `_inbox/sentinel-drafts/`.**

The following actions are PROHIBITED and must not occur during execution of this skill:

- Writing to the live prettyflyforai.com site or any connected repo
- Opening a pull request or committing to any branch
- Sending, scheduling, or publishing any content
- Calling any paid SEO API (DataForSEO, Ahrefs, SEMrush, etc.) without a cleared tool-adoption trigger
- Running any background crawl, cron job, or polling loop
- Writing to any file outside `~/Projects/marketing/_inbox/sentinel-drafts/`

If any step in the procedure would require one of the above actions, stop, note the blocker, and route to the appropriate profile:
- Strategy decision → Marin
- Page copy → Quill
- Claim critique → Stet
- Deployment → Alex (verify-then-deploy)
