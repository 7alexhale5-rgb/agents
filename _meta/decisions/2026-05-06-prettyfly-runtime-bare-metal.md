---
adr: 006
title: PrettyFly Runtime — bare-metal-first commitment + Phase 4.7 insertion
date: 2026-05-06
status: accepted
supersedes: none
amends:
  - 2026-05-04-adopt-hermes.md (re-scopes Hermes from "runtime" to "frozen reference implementation")
related:
  - 2026-05-04-adopt-hermes.md
  - 2026-05-04-vanclief-world-model-audit.md
  - 2026-05-05-substrate-architecture.md
  - 2026-05-05-slack-ecosystem-pivot.md
  - 2026-05-05-litellm-routing-stack.md
research:
  - 2026-05-06-jack-roberts-thesis-bare-metal-hermes-replacement.md
  - 2026-05-04-hermes-agent-unified-overhaul.md
  - 2026-05-04-company-agi-laik-hermes-fusion.md
operator_authorization: |
  "We commit to all six yeses for the six locks, default decisions. I also want to have a deep
  planning session to realign with the idea that it's more important for us to build this and
  replicate it ourselves. Let's move forward with that understanding and act as a 1% agentic
  system engineer would." — Alex, 2026-05-06 morning
---

# ADR-006 — PrettyFly Runtime, bare-metal-first commitment

## Context

ADR-001 adopted Hermes Agent (Nous Research, MIT, v0.12.0) as the unified runtime. That decision held for two operational days. In that window:

1. Cross-source research (Anthropic's _Building Effective Agents_, Karpathy's `autoresearch`, Artiquare's framework critique, Andrew Wilkinson's Harbor migration, Jack Roberts' "I replaced Hermes" thesis, with LangChain's official defense weighed as counterpoint) converged uniformly on the position that **for a multi-profile fleet with a multi-tenant marketplace, owning the runtime beats consuming a third-party shell**.
2. The local Hermes install drifted from `v0.12.0 (2026.4.30)` to "**261 commits behind upstream**" within those same two days — empirical confirmation of the "their roadmap, not yours" failure mode.
3. The substrate stack we have already built — LAIK world model (custom), agentskills.io standard (open), 4D senses (custom), Codex review (open + custom skill), 13-profile org (custom), PrettyFly OS marketplace (custom), LiteLLM routing (open) — is already **~70% custom**. The runtime loop, channel gateway, multi-agent Kanban, dream loop, and skill self-generation are the only third-party pieces.
4. The technical primitive an agent runtime ships — a while loop with a step counter, message history, and tool dispatch — is ~50 lines of Python. The full feature parity (4-tier memory + skill self-gen + dream loop + channel gateway + Kanban + dashboard) is ~2,500–3,500 LOC of Python plus tests.

## Decision

Make **bare-metal-first** the organizing principle of the agentic OS:

1. **PrettyFly Runtime (PF Runtime) is the canonical runtime.** It does not yet exist. We will build it ourselves at `~/Projects/agents/pf-runtime/`, MIT-licensed, ~2,500–3,500 LOC of Python.
2. **Hermes v0.12.0 is reframed as a frozen reference implementation.** ADR-001 stands as the right call for Phase 0 — it gave us conventions (`SOUL.md` / `MEMORY.md` / `USER.md` / `CLAUDE.md`), the OpenClaw migrator, and a working 13-profile cutover path. We keep all of those. We will **not** run `hermes update`. We will read the Hermes source as a reference when implementing PF Runtime equivalents, port targeted security fixes manually, and decommission the Hermes install at the Phase 4.7 cutover.
3. **The pivot does not disrupt active work.** Phase 1, Phase 1.5, the Slack ecosystem pivot (ADR-004), the LiteLLM routing stack (ADR-005), and Phase 4.5 (LAIK-as-MCP fusion) all proceed as planned, on Hermes v0.12.0.
4. **A new Phase 4.7 ships PF Runtime via 14-day parallel shadow** between LAIK-as-MCP fusion (Phase 4.5) and gravity-claw retirement (Phase 5). Cutover criterion is data-driven (Promptfoo eval ≥ 85% per profile, Ragas faithfulness ≥ 0.85, Langfuse trace volume ±5%, cost-per-session within 10% of the Hermes baseline, zero P0 incidents during the shadow window). If any gate fails, stay on Hermes and document gaps. **No hybrid mode** — the whole point is owning the runtime; running both forever defeats the thesis.

## The six locked commitments (Alex, 2026-05-06)

| #   | Commitment                                                                                                                                                                     | Decision | Status |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------- | ------ |
| 1   | Add Phase 4.7 (PrettyFly Runtime build) between 4.5 and 5                                                                                                                      | **Yes**  | Locked |
| 2   | Continue Phase 1 unchanged on Hermes v0.12.0                                                                                                                                   | **Yes**  | Locked |
| 3   | Pin Hermes at v0.12.0 (no `hermes update`); subscribe to releases for security-fix porting only                                                                                | **Yes**  | Locked |
| 4   | Reuse the `agents/hermes/profiles/{name}/` directory layout in PF Runtime; profiles are runtime-portable markdown                                                              | **Yes**  | Locked |
| 5   | PF Runtime lives at `~/Projects/agents/pf-runtime/`, MIT-licensed, sibling to `hermes/`, `honcho/`, `marketplace/`. Eligible for inclusion in Scale-tier on-prem deliverables. | **Yes**  | Locked |
| 6   | Cutover criterion is data-driven from a 14-day parallel shadow. No hybrid mode after cutover.                                                                                  | **Yes**  | Locked |

## Phase 4.7 sub-phases (Karpathy ladder)

Each sub-phase ships **one thing end-to-end against a measured number**. The gate is a measurement, not a checklist. Phases never collapse — faster gate clearance is velocity, not a license to skip.

| Sub-phase                      | Build (one thing end-to-end)                                                                                                                                                                                                                                                                                                                                                                                                                    | Measured gate                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **4.7.1 — Loop primitive**     | `pf_runtime/runtime/{loop,model_adapter,tool_dispatch,stop_condition,audit}.py` running the `personal` profile through one Slack DM round-trip via LiteLLM proxy                                                                                                                                                                                                                                                                                | Same prompt → same tool calls → ≤ 5% token delta vs Hermes baseline on 30 golden questions                                                                                                                                                                                                                                                                                                         |
| **4.7.2 — Memory + skills**    | 4-tier memory (SOUL / buffer / episodic via LAIK MCP / skills) + skill self-generation + dream loop, running 24h on `personal`                                                                                                                                                                                                                                                                                                                  | Ragas faithfulness ≥ 0.85 on 30-question golden set; ≥ 1 skill auto-authored after 5+ tool-call session; dream-loop produces non-empty post-session pruning diff                                                                                                                                                                                                                                   |
| **4.7.3 — Channel gateway**    | Slack adapter first (pivots from ADR-004) — Socket Mode + 13 OAuth-scoped apps; then Telegram, Email, Discord, optional voice via `file_shared` events                                                                                                                                                                                                                                                                                          | Per-message identical action across runtimes for 50-message corpus on `atlas-ceo`; money-pipeline OAuth scopes still read-only-only on `vanclief` and `sportsbook`                                                                                                                                                                                                                                 |
| **4.7.4 — Kanban + dashboard** | **Postgres-backed** task board (sibling schema in mission-control's existing Neon Postgres; SQLite was original spec but replaced per architecture-finding-3 + concurrency-finding-A in PLAN.md §5/§10) + REST/WebSocket API + Fleet Console extension at `prettyfly-os/` (replaces Hermes' v0.12 Kanban). **Note:** Tier 2 memory buffer remains SQLite per MEMORY_LIFECYCLE.md (per-profile, low-concurrency); only Kanban moves to Postgres. | 13-profile fleet runs on PF Runtime in shadow alongside Hermes for 14 days; trace volume ±5%; **p95 latency ≤150% of baseline + concurrent throughput ≥80% of baseline** (replaces backward-looking cost ±10%); zero P0 incidents; **per-profile real-job execution** ≥1 full real-world job per profile during shadow                                                                             |
| **4.7.5 — Cutover**            | Operator decision against the gate measurements; Hermes service stop; profile dirs flip from `~/.hermes/profiles/` mirror to PF Runtime native                                                                                                                                                                                                                                                                                                  | The five gates: (1) Promptfoo Wilson lower-CI ≥ 85% per profile, (2) Ragas ≥ Hermes baseline – 0.02, (3) **per-profile real-job execution** (every profile completes ≥1 full real-world job through PF Runtime), (4) **p95 latency ≤150% of Hermes baseline + concurrent throughput ≥80% of baseline**, (5) zero P0 incidents — **all five must pass**; otherwise stay on Hermes and document gaps |

## What changes in the existing architecture documents

| Document                                                         | Change                                                                                                                                                                                                                                             |
| ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `docs/migration-runbook.md`                                      | Insert Phase 4.7 between 4.5 and 5 (5 sub-phases, calendar 4–6 weeks). Add note: Hermes pinned at v0.12.0 from this ADR forward.                                                                                                                   |
| `_meta/decisions/2026-05-04-adopt-hermes.md` (ADR-001)           | Append "**Amended by ADR-006 (2026-05-06):** Hermes v0.12.0 reframed from 'unified runtime' to 'frozen reference implementation through Phase 4.7 cutover'. ADR-001's reasoning still holds for Phase 0; this ADR re-scopes the runtime decision." |
| `_meta/decisions/2026-05-05-substrate-architecture.md` (ADR-003) | No change. Substrate primitives (registry, validate-profile, a2a-cards, agora brand) survive runtime swap; PF Runtime reads the same primitives.                                                                                                   |
| `_meta/decisions/2026-05-05-slack-ecosystem-pivot.md` (ADR-004)  | No change. Slack stays the channel; PF Runtime's Slack adapter (Phase 4.7.3) is built to the same hermes-slack toolset spec for behavioral parity.                                                                                                 |
| `_meta/decisions/2026-05-05-litellm-routing-stack.md` (ADR-005)  | No change. LiteLLM proxy + per-agent budgets are runtime-agnostic; PF Runtime points at `http://127.0.0.1:4000` exactly like Hermes does.                                                                                                          |
| `~/.claude/plans/before-we-start-make-ticklish-island.md`        | Append Phase 4.7 section + reference to this ADR.                                                                                                                                                                                                  |

## What stays untouched

- Phase 1 (personal profile shadow vs gravity-claw): runs to completion on Hermes v0.12.0.
- Phase 1.5 (Honcho stand-up + Slack pairing): runs to completion on Hermes v0.12.0.
- Phase 2 (mike-lawdbot migration): uses `hermes claw migrate`, retains BOT_TOKEN rotation procedure.
- Phase 3 (paperclip activation): runs on Claude Max subscription via Hermes adapters.
- Phase 4 (Mission Control retirement, Slack cutover from ADR-004): runs on Hermes v0.12.0.
- Phase 4.5 (LAIK-as-MCP fusion): builds the LAIK MCP boundary that PF Runtime will consume in 4.7. **The MCP-not-Python boundary becomes load-bearing for Phase 4.7** — see "Pre-work" below.
- All 13 profiles' SOUL/USER/MEMORY/CLAUDE/manifest/config/a2a-card files: portable across runtimes, no rewrites.
- agentskills.io skill format: portable.
- LiteLLM proxy + tier mapping + per-agent budgets: runtime-agnostic.
- 4D senses MCP server: runtime-agnostic.
- Honcho server-side use (AGPL): unchanged; PF Runtime consumes via its existing API.
- Codex parallel-review skill at `~/.agents/skills/staged-review/`: env-scope, unchanged.
- VanClief world-model audit duty (ADR-002): unchanged; expands at Phase 4.7 to audit cross-runtime parity during the shadow window.

## Pre-work that fires NOW (in parallel with Phase 1)

These are pure design / scaffolding tasks. They do not touch the active Phase 1 shadow window. They reduce Phase 4.7 risk by locking interfaces before the build.

1. **PF Runtime public API spec** — write `pf-runtime/SPEC.md` defining the runtime surface: profile loader contract, channel adapter ABC, tool dispatch protocol, memory tier interfaces, kanban store schema. ~1 day.
2. **LAIK MCP boundary lock** — Phase 4.5 will produce `mcp-servers/laik/` already. Confirm the MCP surface is **stable enough that PF Runtime consumes it identically to Hermes**. If anything is Hermes-specific, refactor before 4.5 ships. ~2 hours.
3. **Profile-dir contract test** — write a tiny test `tests/profile_dir_contract.py` that asserts a profile dir loadable by both Hermes (today) and PF Runtime (future). Run it nightly across all 13 profiles starting now. ~3 hours.
4. **Hermes commit-watcher** — daily `git -C ~/.hermes/hermes-agent/ log --oneline HEAD..origin/main | head -50` mailed to `forge-audit` profile. We're not pulling, but we need to _see_ what we're not pulling. ~30 minutes.

## Reversibility

- **Reversible until Phase 4.7.5 cutover decision.** If the shadow gate fails, we stay on Hermes and document gaps. Sunk cost in PF Runtime is the source code itself, which keeps value as either: (a) input to a future second attempt, or (b) a clean export-able bare-metal runtime SKU for technical-tier tenants who want to fork.
- **Irreversible after cutover** — Hermes service is stopped, runtime mirror dirs in `~/.hermes/profiles/` flip to canonical at `pf-runtime/runtime-state/profiles/`. Reverting after cutover is a fresh 1–2 week migration, not a flip.
- The 14-day shadow window is the irreversibility gate. We hold the line — if any of the five gate measurements fail, we do not cut over.

## Stop conditions

- **PF Runtime build exceeds 4,500 LOC** without feature-parity for the four sub-phases: hold the line, drop sub-phases by priority (Kanban can defer; channel gateway cannot).
- **Sub-phase 4.7.1 token-delta exceeds 5% on golden set**: stop, measure, fix the loop primitive before continuing. The loop is load-bearing for everything else.
- **Hermes ships a security-relevant fix between now and Phase 4.7 cutover**: port manually, do **not** run `hermes update`. The integrity of pinning is the whole strategy.
- **Operator decides bare-metal isn't the right call after seeing the v0.1 prototype**: stop building, ship the prototype as a reference for future revisitation, continue on Hermes.

## Consequences

**Wins**

- Total source ownership through to the agent loop. Every line is debuggable in our IDE.
- "Their roadmap, not yours" failure mode eliminated permanently.
- Tighter LAIK integration: PF Runtime can fast-path LAIK MCP calls instead of round-tripping through Hermes' generic MCP layer.
- Per-tenant cost ceiling enforcement at the runtime layer (paired with LiteLLM's per-key budget caps).
- Marketplace SKU consistency: three tiers (Lite/Pro/Scale) all run the same MIT-licensed runtime, with feature flags swapping the surface area.
- Sixth competitive moat: open runtime source. Glean / Hebbia / Sierra / Decagon / Microsoft Copilot Tuning don't have this.

**Costs**

- 4–6 weeks of focused build time (estimate: ~2,500–3,500 LOC + ~600 LOC tests, may exceed).
- 14-day shadow window draws 2× LLM cost (PF Runtime + Hermes both running). Mitigation: shadow runs with `tier-cheap` defaults during the window.
- Maintenance ownership transfers from Nous Research to us. We absorb security-fix work and feature drift.
- Loss of access to Hermes' ecosystem (community plugins, future v0.13+ features) — accepted by the thesis.

## Cross-references

- Companion research (synthesis behind this ADR): `~/Projects/research-vault/research/2026-05-06-jack-roberts-thesis-bare-metal-hermes-replacement.md`
- Hermes adoption ADR (now amended): `_meta/decisions/2026-05-04-adopt-hermes.md`
- VanClief world-model audit (expands at Phase 4.7): `_meta/decisions/2026-05-04-vanclief-world-model-audit.md`
- Substrate architecture (unchanged): `_meta/decisions/2026-05-05-substrate-architecture.md`
- Slack ecosystem pivot (unchanged, informs Phase 4.7.3): `_meta/decisions/2026-05-05-slack-ecosystem-pivot.md`
- LiteLLM routing stack (unchanged, runtime-agnostic): `_meta/decisions/2026-05-05-litellm-routing-stack.md`
- Migration runbook (Phase 4.7 inserted): `docs/migration-runbook.md`
- Surgical plan (Phase 4.7 appended): `~/.claude/plans/before-we-start-make-ticklish-island.md`
- Detailed Phase 4.7 plan (forthcoming, generated by `/planning-stack --deep --tech` immediately after this ADR commits): `.planning/phase-4-7-prettyfly-runtime/PLAN.md`
