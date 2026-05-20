---
name: critique-campaign-brief
description: Critique one campaign brief at ~/Projects/marketing/campaigns/<name>/campaign-brief.md. Apply kill-list, tool-trigger, do-not-scale, market-thesis tests. Verdict SHIP/REVISE/KILL.
input: campaign slug (e.g. "prettyfly-ai-ops-audit-v0")
output: markdown to ~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-critique-campaign-{slug}.md + paired stet.critique.proposed PFOS event
---

# Skill: critique-campaign-brief

## Purpose

Read one campaign brief, apply campaign-level tests (kill-list, tool-trigger, do-not-scale, market-thesis alignment), end with a verdict. Distinct from `critique-draft` (single-artifact-level) — this targets the campaign's own thesis + plan.

## Hard scope rules

- Read-only on the campaign brief and the campaign dir.
- Cite a vault file for every flagged finding.
- No rewrite generation — CMO + Alex revise the brief, not Stet.

## Inputs

1. `SOUL.md`, `DOCTRINE.md`, `MEMORY.md`
2. Target campaign dir at `~/Projects/marketing/campaigns/<campaign-slug>/`:
   - `README.md` (campaign goal, state, loop, current next-move)
   - `campaign-brief.md` (the brief being critiqued)
   - Any other artifacts in the dir (scorecard, outreach-message-set, linkedin-content-sprint)
3. `~/Projects/marketing/brand/market-thesis-v0.md` — positioning anchor
4. `~/Projects/marketing/brand/buyer-belief-ladder.md` — buyer journey
5. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md`
6. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md`
7. `~/Projects/marketing/metrics/weekly-revenue-loop-v0.md` — "do not scale" rule
8. `~/Projects/marketing/metrics/message-outcome-ledger-v0.md` — actual buyer language
9. `~/Projects/marketing/agents/cmo-operating-brief.md` — CMO charter (campaign briefs route through CMO)

## Procedure

1. **Read the campaign dir fully.** Parse README + campaign-brief + adjacent assets.

2. **Check kill triggers (verdict = KILL on any hit):**
   - **Kill-list violation**: does the brief propose any killed item or rest on a killed assumption?
   - **Tool-adoption-trigger violation**: does the brief assume or recommend a tool whose trigger hasn't fired?
   - **Do-not-scale violation**: does the brief recommend scaling (more volume, more channels, automation, paid ads) without a buyer-named or buyer-corrected real workflow in evidence (check `message-outcome-ledger-v0.md`)?
   - **Positioning drift**: does the brief contradict the AI Liberation thesis from `market-thesis-v0.md` (pitches "more AI" instead of useful systems, treats PrettyFly as generic AI agency or deck-only shop)?
   - **Invented evidence**: does the brief cite a metric / customer name / reply count / conversion number / buyer language NOT in any vault source?

3. **Sweep the brief itself for clarity + completeness** (warn-level, not KILL-level):
   - Goal: is it ONE measurable outcome, or a pile?
   - Audience: cites a specific ICP segment from `prettyfly-company-truth.md § First 30-Day Audience`?
   - Offer: maps to a specific entry in `offers/revenue-ladder.md`?
   - Channels: only authorized channels named (per `channel-positioning-map-v0.md`)?
   - Next move: ONE smallest manual action named, not a system build (per `weekly-revenue-loop-v0.md`)?
   - Stop condition: named? (When does the campaign get re-decided?)
   - Success metric: a buyer behavior (booked diagnostic, named workflow), not a vanity metric (impressions, likes)?

4. **Apply inversion** (per `DOCTRINE.md § Inversion`): "If this campaign failed badly six months from now, what plausible causes?" Name 2-4 causes; map each to a finding (or a finding that should exist but doesn't yet).

5. **Apply door classification** (per `DOCTRINE.md § Door classification`): is the campaign two-way or one-way? If one-way (paid ads ramp, public positioning change, CRM lock-in, hiring), what approval gate must Alex clear before launch? One-way without a named gate = `critical` finding.

6. **Decide verdict.** Kill trigger → `KILL`. Otherwise 1+ critical or 3+ warn → `REVISE`. Otherwise `SHIP`.

7. **Write critique** to `~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-critique-campaign-{slug}.md`. `target_artifact_type: campaign-brief`. Body MUST include `## Inversion` and `## Door classification` sections.

8. **Emit PFOS event**:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile stet \
  --tool critique_campaign.propose \
  --readout-path "_inbox/stet-critiques/<YYYY-MM-DD>-critique-campaign-<slug>.md" \
  --extra-json '{"verdict":"<SHIP|REVISE|KILL>","critical":<N>,"warn":<N>,"info":<N>,"kill_triggers_hit":[<list>],"door":"<two-way|one-way>","target_artifact_path":"campaigns/<slug>/campaign-brief.md"}'
```

## Anti-patterns

- Critiquing a campaign brief without reading the campaign README (campaigns are about the loop, not just the brief)
- Inversion sections that name vague risks ("buyers might not respond") — every cause maps to a specific finding
- Door classification missing on a campaign-level critique
- Skipping the kill triggers and running sweeps anyway when a kill is already obvious

## Failure modes

- Campaign dir missing or unreadable → return error
- `campaign-brief.md` missing → produce a critique with one `critical` finding ("brief file missing — campaign cannot be reviewed without it") and verdict `REVISE`
- Vault `metrics/` files missing → cannot run do-not-scale check; flag with `info` finding + verdict at most `REVISE`
