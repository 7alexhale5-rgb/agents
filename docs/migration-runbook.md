# Migration runbook — $1M ARR agent fleet (post-pivot)

> **Status pointer:** $1M-pivot Phase 2 (CMO weekly decision pilot) — in progress 2026-05-18. PF Runtime archived; Hermes Agent v0.12.0 is the canonical runtime.

## Context

The 2026-05-18 $1M pivot dropped the PFOS agent marketplace and reset the agent fleet around revenue-pipeline roles. Thirteen non-revenue profiles moved to `hermes/_archive/2026/`. PrettyFly Runtime moved to `_archive/2026/pf-runtime/`. The plan driving this is [`~/.claude/plans/here-is-what-we-joyful-torvalds.md`](../../.claude/plans/here-is-what-we-joyful-torvalds.md).

The earlier multi-phase Hermes-consolidation runbook is preserved at [`_archive/2026/docs/migration-runbook-pre-pivot.md`](../_archive/2026/docs/migration-runbook-pre-pivot.md) for historical record. The phases below are the live ones.

## Phase index

| Phase | Goal                                                                                         | Status                                  |
| ----- | -------------------------------------------------------------------------------------------- | --------------------------------------- |
| 1     | Archive dead weight (pf-runtime, marketplace, 13 non-revenue profiles)                       | ✅ Landed 2026-05-18 (commit `7e1340c`) |
| 1.5   | PrettyFly sub-project revenue audit                                                          | 🟡 In progress                          |
| 2     | Build CMO profile from Atlas template                                                        | 🟡 In progress                          |
| 3     | Build Quill + Viper profiles from Atlas template                                             | ⬜ Not started                          |
| 4     | Extend Atlas with marketing-vault read path                                                  | ⬜ Not started                          |
| 5     | Build koho-ops + yeh-ops retainer-delivery profiles                                          | ⬜ Not started                          |
| 5.5   | Rebuild codex profile from Atlas template                                                    | ⬜ Not started                          |
| 6     | Wake one dormant Hermes capability (trigger-gated per the sub-project → profile trigger ADR) | ⬜ Not started                          |
| 7     | Quarterly compound review                                                                    | Next: 2026-08-18                        |

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

| Profile     | Status                                          | Phase |
| ----------- | ----------------------------------------------- | ----- |
| `atlas-ceo` | Live (template, rung 3)                         | —     |
| `cmo`       | Live (scaffolded 2026-05-18)                    | 2     |
| `quill`     | Not built                                       | 3     |
| `viper`     | Not built                                       | 3     |
| `koho-ops`  | Not built                                       | 5     |
| `yeh-ops`   | Not built (rebuild clean; old version archived) | 5     |
| `codex`     | Live (rebuild from Atlas template pending)      | 5.5   |

## Archived (2026-05-18)

Profiles moved to `hermes/_archive/2026/`: `atelier`, `consultops`, `forge-audit`, `lawdbot`, `mobile`, `ops`, `personal`, `personal-baseline`, `quill-content`, `sportsbook`, `vanclief`, `viper-outreach`, `yeh-ops`.

Code moved to `_archive/2026/`: `pf-runtime/`, `marketplace/`.

## Phase 1 — archive dead weight (done)

Commit `7e1340c` (2026-05-18) physically moved 13 profile dirs + the `pf-runtime/` tree + the `marketplace/` tree under `_archive/2026/`. New roster locked: `atlas-ceo`, `cmo`, `quill`, `viper`, `koho-ops`, `yeh-ops`, `codex`.

## Phase 1.5 — PrettyFly sub-project revenue audit (in progress)

Audit each sub-project against the trigger rule from `_meta/decisions/2026-05-18-subproject-to-profile-trigger.md` (30 consecutive days of $2k/mo OR 3hr/week × 4wks OR 3 paying customers). Demote any that don't trigger; promote any that do.

Sub-projects under audit: `audit-engine`, `decision-maker-identifier`, LAIK, `gravity-stack-koho-starter`, others per `~/Projects/MANIFEST.md`.

## Phase 2 — build CMO profile (in progress)

CMO is the marketing operating agent. Reads the marketing vault, runs the weekly revenue loop, proposes ONE weekly decision (continue / narrow ICP / rewrite message / change channel / pause). Never publishes, sends, or schedules external messages.

**Acceptance**: CMO ships one weekly readout against the AI Ops Audit campaign through the supervised dispatch packet.

**Current state**: `hermes/profiles/cmo/` exists with SOUL, DOCTRINE, USER, MEMORY, CLAUDE, manifest, a2a-card, config, plus the `buyer-signal-router` and `supervised-dispatch` skills (per 2026-05-18 commit `9270bfc` + `a9e811d`).

## Phase 3 — build Quill + Viper (not started)

- **Quill**: drafts content from approved positioning in the marketing vault. Drafts to `_inbox/`, never publishes.
- **Viper**: pressure-tests campaigns, claims, positioning, and campaign logic before launch.

Both built from the Atlas template per the 11-file contract.

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

Edit this line as phases complete: **Current phase: $1M-pivot Phase 2 (CMO weekly decision pilot) — in progress 2026-05-18.**
