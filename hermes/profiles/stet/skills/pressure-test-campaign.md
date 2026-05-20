---
name: pressure-test-campaign
description: Pre-launch pressure test of a whole campaign. Inversion + door classification + adversarial sweeps across the entire campaign dir. Strongest pre-launch gate before any campaign goes live.
input: campaign slug (e.g. "prettyfly-ai-ops-audit-v0") + launch scope ("public-content" | "outreach" | "paid" | "full-launch")
output: markdown to ~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-pressure-test-{slug}.md + paired stet.critique.proposed PFOS event
---

# Skill: pressure-test-campaign

## Purpose

Pre-launch pressure test of a whole campaign — distinct from `critique-campaign-brief` (single-brief critique) and `critique-draft` (single-artifact critique). This skill runs when Alex is about to take a campaign live and wants Stet to surface every plausible failure mode before launch budget or public surface area gets committed.

## Hard scope rules

- Run only when Alex or CMO explicitly invokes for a pre-launch decision. Not a routine review.
- Read-only across the entire campaign dir + adjacent vault inputs.
- Verdict is binding for the launch scope named in the input — `SHIP` means Alex can launch under that scope; `REVISE` means hold launch until findings addressed; `KILL` means do not launch this scope, period.
- Inversion + door classification are mandatory body sections.

## Inputs

1. `SOUL.md`, `DOCTRINE.md`, `MEMORY.md`
2. Entire campaign dir at `~/Projects/marketing/campaigns/<campaign-slug>/`:
   - `README.md`, `campaign-brief.md`, `scorecard-v0.md`, `outreach-message-set.md`, `linkedin-content-sprint.md`, any other assets
3. The campaign's full provenance list (frontmatter `provenance:` in README) — every linked vault file
4. `~/Projects/marketing/brand/market-thesis-v0.md`, `brand/buyer-belief-ladder.md`, `brand/public-trust-path-activation-2026-05-18.md`
5. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md`, `decisions/2026-05-16-tool-adoption-triggers.md`
6. `~/Projects/marketing/metrics/weekly-revenue-loop-v0.md` — do-not-scale rule + revenue loop cadence
7. `~/Projects/marketing/metrics/message-outcome-ledger-v0.md` — actual buyer language baseline
8. `~/Projects/marketing/metrics/marketing-signal-contract-v0.md` — signal contract (what events the campaign produces)
9. `~/Projects/marketing/agents/cmo-operating-brief.md` — CMO charter

## Procedure

1. **Confirm launch scope.** Acceptable values: `public-content` (LinkedIn posts, content drops), `outreach` (DMs, connection notes), `paid` (paid ads, sponsored placements), `full-launch` (all of the above + supporting infra). If scope is `paid` or `full-launch`, the door is one-way by default — flag accordingly in step 5.

2. **Read the campaign dir end-to-end.** Note every artifact's status, any unfinished sections, any mismatches between README state and actual artifact content.

3. **Check kill triggers (verdict = KILL on any hit):**
   - Kill-list violations across any artifact in the dir
   - Tool-adoption-trigger violations across any artifact
   - Do-not-scale violation: is the launch scope `paid` or `full-launch` without buyer-named workflow evidence in `message-outcome-ledger-v0.md`?
   - Positioning drift across any artifact
   - Invented evidence across any artifact
   - Signal-contract violation: does the campaign produce signals that DON'T map to `marketing-signal-contract-v0.md`? (per its own "no new surface gets built unless its signal maps to the contract" rule)

4. **Run the 7 sweeps across every artifact in the dir.** Tally per-artifact findings. Sum severity.

5. **Door classification** (mandatory). Two-way or one-way based on launch scope:
   - `public-content`: usually two-way (a post can be deleted, learning is cheap)
   - `outreach`: usually two-way for manual DMs, one-way if introducing automation or scale ramp
   - `paid`: ALWAYS one-way (spend committed)
   - `full-launch`: ALWAYS one-way (positioning + spend + public surface all change together)
     For one-way doors, name the approval gate Alex must clear (cost ceiling, time box, kill-switch condition).

6. **Inversion (mandatory).** "If this campaign failed badly six months from now under the named launch scope, what 3-5 plausible causes?" Map each cause to:
   - A finding in this pressure-test (existing finding F# or new finding F#)
   - A vault standard that, if applied earlier, would have prevented it (or "no vault standard exists yet — flag for Alex to set one")

7. **Kill-switch condition.** For any non-KILL verdict at `paid` or `full-launch` scope, name a kill-switch condition: "Stop this launch and review if X happens within Y days." This becomes part of the SHIP verdict — Alex commits to honoring it before launch.

8. **Decide verdict.** Kill trigger → `KILL`. 1+ critical OR (one-way door without approval gate or kill-switch condition) → `REVISE`. Otherwise `SHIP`.

9. **Write pressure-test** to `~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-pressure-test-{slug}.md`. `target_artifact_type: pre-launch-pressure-test`. Body MUST include: `## Verdict`, `## Findings` (numbered, severity-graded), `## Inversion`, `## Door classification` (with approval gate if one-way), `## Kill-switch condition` (if one-way and verdict SHIP), `## Sweeps run` (per artifact).

10. **Emit PFOS event**:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile stet \
  --tool pressure_test.propose \
  --readout-path "_inbox/stet-critiques/<YYYY-MM-DD>-pressure-test-<slug>.md" \
  --extra-json '{"verdict":"<SHIP|REVISE|KILL>","critical":<N>,"warn":<N>,"info":<N>,"kill_triggers_hit":[<list>],"launch_scope":"<scope>","door":"<two-way|one-way>","kill_switch":"<condition or null>"}'
```

## Anti-patterns

- Running pressure-test on a routine basis — this is a launch gate, not a status review
- SHIP verdict on a one-way door without a kill-switch condition
- Inversion sections that don't map causes to specific findings
- "Soft" KILL ("maybe don't launch yet") — pick a verdict
- Generating the revised campaign — that's CMO + Alex, not Stet

## Failure modes

- Launch scope not provided → return with one `critical` finding asking for scope, verdict `REVISE`
- Campaign dir missing key artifacts → critical findings naming each missing piece, verdict at minimum `REVISE`
- Vault metrics files missing → cannot run do-not-scale check; verdict cap at `REVISE` until check is possible
- Buyer-named workflow evidence in `message-outcome-ledger-v0.md` is sparse or contradicted → cap verdict at `REVISE` for any `paid` or `full-launch` scope
