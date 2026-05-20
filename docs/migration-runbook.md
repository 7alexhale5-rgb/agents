# Migration runbook — $1M ARR agent fleet (post-pivot)

> **Status pointer:** $1M-pivot Phase 3 (Quill + Stet scaffolded) — landed 2026-05-20. PF Runtime archived; Hermes Agent v0.12.0 is the canonical runtime.

## Context

The 2026-05-18 $1M pivot dropped the PFOS agent marketplace and reset the agent fleet around revenue-pipeline roles. Thirteen non-revenue profiles moved to `hermes/_archive/2026/`. PrettyFly Runtime moved to `_archive/2026/pf-runtime/`. The plan driving this is [`~/.claude/plans/here-is-what-we-joyful-torvalds.md`](../../.claude/plans/here-is-what-we-joyful-torvalds.md).

The earlier multi-phase Hermes-consolidation runbook is preserved at [`_archive/2026/docs/migration-runbook-pre-pivot.md`](../_archive/2026/docs/migration-runbook-pre-pivot.md) for historical record. The phases below are the live ones.

## Phase index

| Phase | Goal                                                                                         | Status                                             |
| ----- | -------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| 1     | Archive dead weight (pf-runtime, marketplace, 13 non-revenue profiles)                       | ✅ Landed 2026-05-18 (commit `7e1340c`)            |
| 1.5   | PrettyFly sub-project revenue audit                                                          | 🟡 In progress                                     |
| 2     | Build CMO profile from Atlas template                                                        | ✅ Landed (commit `776d981` + iterations)          |
| 3     | Build Quill + Stet profiles from Atlas template                                             | 🟡 Scaffolded 2026-05-20; awaiting first event row |
| 4     | Extend Atlas with marketing-vault read path                                                  | ⬜ Not started                                     |
| 5     | Build koho-ops + yeh-ops retainer-delivery profiles                                          | ⬜ Not started                                     |
| 5.5   | Rebuild codex profile from Atlas template                                                    | ⬜ Not started                                     |
| 6     | Wake one dormant Hermes capability (trigger-gated per the sub-project → profile trigger ADR) | ⬜ Not started                                     |
| 7     | Quarterly compound review                                                                    | Next: 2026-08-18                                   |

## Hermes pin

Hermes Agent v0.12.0 (2026.4.30) is the canonical runtime. Do not run `hermes update` — port security-relevant fixes manually. The v0.12.0 pin holds indefinitely.

## Authoritative specs

- $1M plan (drives this runbook): [`~/.claude/plans/here-is-what-we-joyful-torvalds.md`](../../.claude/plans/here-is-what-we-joyful-torvalds.md)
- Profile shape contract: [`_meta/decisions/2026-05-18-agent-shape-11-file-contract.md`](../_meta/decisions/2026-05-18-agent-shape-11-file-contract.md)
- Sub-project → profile trigger: [`_meta/decisions/2026-05-18-subproject-to-profile-trigger.md`](../_meta/decisions/2026-05-18-subproject-to-profile-trigger.md)
- Hermes → PFOS event contract: [`_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`](../_meta/decisions/2026-05-18-hermes-pfos-event-contract.md)
- Shared-handoff skill: [`_meta/decisions/2026-05-18-generate-handoff-shared-skill.md`](../_meta/decisions/2026-05-18-generate-handoff-shared-skill.md)
- Historical ADRs (superseded): [`ADR-006 PF Runtime bare-metal`](../_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md), [`ADR-007 hybrid runtime lanes`](../_meta/decisions/2026-05-16-agentic-os-hybrid-runtime-lanes.md)

## Live profile roster (target: 7)

| Profile     | Status                                                                          | Phase |
| ----------- | ------------------------------------------------------------------------------- | ----- |
| `atlas-ceo` | Live (template, rung 3)                                                         | —     |
| `cmo`       | Live (scaffolded 2026-05-18; emitter pattern wired via patch #5)                | 2     |
| `quill`     | Live (scaffolded 2026-05-20, lint PASS, awaiting first draft + paired event)    | 3     |
| `stet`     | Live (scaffolded 2026-05-20, lint PASS, awaiting first critique + paired event) | 3     |
| `koho-ops`  | Not built                                                                       | 5     |
| `yeh-ops`   | Not built (rebuild clean; old version archived)                                 | 5     |
| `codex`     | Live (rebuild from Atlas template pending)                                      | 5.5   |

## Archived (2026-05-18)

Profiles moved to `hermes/_archive/2026/`: `atelier`, `consultops`, `forge-audit`, `lawdbot`, `mobile`, `ops`, `personal`, `personal-baseline`, `quill-content`, `sportsbook`, `vanclief`, `stet-outreach`, `yeh-ops`.

Code moved to `_archive/2026/`: `pf-runtime/`, `marketplace/`.

## Phase 1 — archive dead weight (done)

Commit `7e1340c` (2026-05-18) physically moved 13 profile dirs + the `pf-runtime/` tree + the `marketplace/` tree under `_archive/2026/`. New roster locked: `atlas-ceo`, `cmo`, `quill`, `stet`, `koho-ops`, `yeh-ops`, `codex`.

## Phase 1.5 — PrettyFly sub-project revenue audit (in progress)

Audit each sub-project against the trigger rule from `_meta/decisions/2026-05-18-subproject-to-profile-trigger.md` (30 consecutive days of $2k/mo OR 3hr/week × 4wks OR 3 paying customers). Demote any that don't trigger; promote any that do.

Sub-projects under audit: `audit-engine`, `decision-maker-identifier`, LAIK, `gravity-stack-koho-starter`, others per `~/Projects/MANIFEST.md`.

## Phase 2 — build CMO profile (in progress)

CMO is the marketing operating agent. Reads the marketing vault, runs the weekly revenue loop, proposes ONE weekly decision (continue / narrow ICP / rewrite message / change channel / pause). Never publishes, sends, or schedules external messages.

**Acceptance**: CMO ships one weekly readout against the AI Ops Audit campaign through the supervised dispatch packet.

**Current state**: `hermes/profiles/cmo/` exists with SOUL, DOCTRINE, USER, MEMORY, CLAUDE, manifest, a2a-card, config, plus the `buyer-signal-router` and `supervised-dispatch` skills (per 2026-05-18 commit `9270bfc` + `a9e811d`).

## Phase 3 — build Quill + Stet (scaffolded 2026-05-20)

- **Quill**: drafts content from approved marketing-vault positioning. Writes to `~/Projects/marketing/_inbox/quill-drafts/`. Never publishes. Five flat-MD skills: `draft-linkedin-field-note`, `draft-outreach-message`, `draft-campaign-asset`, `revise-from-critique`, plus shared `generate-handoff`. Four `draft_*.propose` tools in `config.yaml` so per-skill attribution is correct in PFOS events.
- **Stet**: pressure-tests drafts, campaign briefs, positioning, and campaigns before launch. Writes to `~/Projects/marketing/_inbox/stet-critiques/`. Never modifies any artifact. Five flat-MD skills: `critique-draft`, `critique-campaign-brief`, `critique-positioning`, `pressure-test-campaign`, plus shared `generate-handoff`. Verdict required on every critique: `SHIP` / `REVISE` / `KILL`. Four `<critique-name>.propose` tools so per-skill attribution stays clean.

Both built from the Atlas template per the 11-file contract. Both inherit the patch #5 emitter pattern (`hermes/lib/agent_events.py` + `scripts/emit-agent-event.py`) — every drafting/critique skill ends with the explicit CLI emission.

**Phase 3 Karpathy gate** (falsifiable in one SQL query):

```sql
SELECT type, cwd_project, skill_slug, surface
FROM public.agent_events
WHERE type IN ('quill.draft.proposed', 'stet.critique.proposed')
  AND cwd_project = 'marketing'
  AND skill_slug IS NOT NULL
  AND surface = 'cli'
  AND created_at > NOW() - INTERVAL '1 hour';
-- expect: 2 rows (one per profile)
```

**Deliberately out of scope this phase** (deferred per 1% CTO assessment):

- Patch #2 (identity-file collapse from 4 → 1 IDENTITY.md across Atlas/CMO/codex) — deferred until 5+ profiles expose actual duplication pain
- Patch #11 (`scripts/new-profile.sh`) — deferred until 3rd+ manual profile copy exposes the actual repetition pattern
- Fix Atlas's missing event block (Atlas predates the emitter) — separate Atlas patch
- Sync archived profiles out of `~/.hermes/profiles/` (drift cleanup) — separate cleanup pass
- Atlas eval path repair (points at archived `pf-runtime/scripts/eval_profile_prompt.py`) — Quill + Stet use `anthropic:messages` provider directly to avoid the broken pattern

## Phase 4 — extend Atlas with marketing-vault read path (not started)

Wire Atlas to read `~/Projects/marketing/` directly (currently advisor-only against the repo). **Acceptance**: Atlas's weekly brief references named items from the marketing vault by relative path.

## Phase 5 — build koho-ops + yeh-ops (not started)

- **koho-ops**: Koho retainer delivery — Marc routing, ConsultOps demos, Excerpa work.
- **yeh-ops**: Yehovah retainer delivery — trial-to-GA monitoring, CTO duties.

Both consume the [`email-triage`](../hermes/shared-skills/email-triage/SKILL.md) shared skill salvaged in this same pivot cleanup.

## Phase 5.5 — rebuild codex from Atlas template (not started)

Codex is the developer helper. Rebuild against the 11-file contract for consistency with the rest of the roster.

## Phase 6 — wake dormant Hermes capability (trigger-gated)

Per the sub-project-to-profile trigger ADR. Reserved for the first capability that earns trigger-gated promotion after Phase 5 ships.

## Phase 7 — quarterly compound review

Next: **2026-08-18**. Audit fleet health against revenue targets, demote unused profiles per the 30-day no-trigger rule, surface candidate profiles from sub-projects that crossed the trigger threshold.

## Operator notes

- Profile additions go through `scripts/lint-profile.sh` before any commit (per the 11-file contract ADR).
- Channel updates emit PFOS `agent_events` per the event-contract ADR. No raw vault text, no prompts, no secrets in payloads.
- Shared skills live in `hermes/shared-skills/`; profile-specific skills in `hermes/profiles/<name>/skills/`.
- Cross-session handoffs use the `generate-handoff` shared skill.

## Phase pointer

Edit this line as phases complete: **Current phase: $1M-pivot Phase 3 (Quill + Stet scaffolded) — landed 2026-05-20; awaiting first event-emission gate.**
