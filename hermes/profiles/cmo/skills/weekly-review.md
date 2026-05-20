---
name: weekly-review
description: Produce a Weekly Readout from the marketing vault. Uses Weekly Revenue Loop v0 cadence. Outputs ONE decision and ONE smallest next action.
input: optional `week_of` date (defaults to current week)
output: markdown to ~/Projects/marketing/_inbox/cmo-readouts/{YYYY-MM-DD}-week-of-{YYYY-MM-DD}.md
---

# Skill: weekly-review

## Purpose

Turn the marketing vault into ONE weekly decision and ONE smallest next action, per the Weekly Revenue Loop v0 cadence.

## Inputs (must read before generating)

1. `~/Projects/marketing/agents/cmo-operating-brief.md` (your charter)
2. `~/Projects/marketing/metrics/weekly-revenue-loop-v0.md` (the cadence definition)
3. `~/Projects/marketing/metrics/weekly-review-template.md` (the output shape)
4. `~/Projects/marketing/metrics/message-outcome-ledger-v0.md` (signal data)
5. `~/Projects/marketing/metrics/first-30-days-scoreboard.md` (targets)
6. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md` (what NOT to propose)
7. Active campaign README (e.g. `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/README.md`)
8. Recent buyer activity: `~/Projects/marketing/outreach/*` for the current sprint period
9. `MEMORY.md` (CMO profile narrative anchors)

## Procedure

1. **Scorecard pass** — fill every row in the Weekly Scorecard table from the Weekly Revenue Loop v0 spec. If a value cannot be sourced, write "no signal" with a one-line note explaining what evidence is missing.

2. **Decision pass** — apply Decision Rules:
   - `continue` — routes open AND buyer language is getting more specific
   - `narrow ICP` — one segment produces materially better workflow language
   - `rewrite message` — right buyers respond weakly or correct the read
   - `change channel` — evidence is strong but route is poor
   - `pause` — no route opens, no workflow appears, signal is too weak

3. **Hard rule check** — if no real workflow has been named or corrected by a buyer, the decision MUST be `pause` or `continue with note: do not scale yet`. Do not propose `narrow ICP` / `rewrite` / `change channel` without buyer evidence.

4. **Smallest next action** — pick ONE from the Manual Action Menu (Weekly Revenue Loop v0). Default to `hold if no real signal exists` when in doubt.

5. **Stop condition** — name the specific condition that would cause the next readout to flip the decision.

6. **PFOS fields to preserve later** — list which scorecard values were most informative this week (future PFOS readout will inherit these).

7. **Kill-list check** — confirm no part of the readout proposes a killed item per `decisions/2026-05-16-marketing-engine-kill-list.md`. If a killed item is being considered, drop it and note the kill-rule violation.

8. **Write** — output to `~/Projects/marketing/_inbox/cmo-readouts/{YYYY-MM-DD}-week-of-{YYYY-MM-DD}.md` using the Weekly Review Template structure.

9. **Emit safe event summary** — after the readout is written, run the canonical emitter:

   ```bash
   source ~/.config/prettyfly-marketing/hermes-tokens.env
   python3 ~/Projects/agents/scripts/emit-agent-event.py \
     --profile cmo \
     --tool weekly_decision.propose \
     --readout-path "_inbox/cmo-readouts/<YYYY-MM-DD>-week-of-<YYYY-MM-DD>.md" \
     --decision <continue|narrow|rewrite|change-channel|pause> \
     --confidence <0.0-1.0>
   ```

   The emitter loads CMO's `config.yaml` event block, builds an ADR-compliant payload (per `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`), and POSTs to PFOS `/api/silos/skills/agent-event`. Successful runs print the inserted row UUID. Do not hand-write the event payload — the contract is enforced by `hermes/lib/agent_events.py`.

## Output shape

Use the One-Page Weekly Readout table from `weekly-review-template.md`. Every cell filled. No empty cells unless explicitly labeled "no signal".

## Anti-patterns to avoid

- Inventing reply counts, prospect names, conversion rates
- Proposing `narrow ICP` without buyer correction evidence
- Recommending tool adoption without trigger condition fired
- Generic marketing-speak ("crushing it", "leverage", "compound", "10x", "moat")
- Quoting CEOs or marketing books for decoration
- Multi-paragraph reflection — keep it operational and short
- Surfacing more than one decision

## Source citation rule

Every factual claim in the readout must cite the vault file it came from (e.g. `Routes opened: 8 — source: message-outcome-ledger-v0.md`). No source = no claim.

## Safe PFOS event shape

```json
{
  "agent_slug": "cmo",
  "type": "cmo.weekly_decision.proposed",
  "status": "pending",
  "surface": "cli",
  "cwd_project": "marketing",
  "skill_slug": "weekly-review",
  "data": {
    "schema_version": "hermes.agent_event.v1",
    "runtime": "hermes",
    "proposal_status": "proposed",
    "decision": "continue",
    "readout_path": "_inbox/cmo-readouts/YYYY-MM-DD-week-of-YYYY-MM-DD.md",
    "private_payload_redacted": true
  }
}
```
