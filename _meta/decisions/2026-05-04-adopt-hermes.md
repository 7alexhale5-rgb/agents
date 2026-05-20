# ADR-001 — Adopt Hermes Agent as the unified runtime

**Date:** 2026-05-04
**Status:** Accepted (amended 2026-05-06 by ADR-006, which itself was superseded by the 2026-05-18 $1M pivot — see header notes)
**Phase:** 0 complete

> **Latest amendment (2026-05-18 $1M pivot, commit `7e1340c`):** The ADR-006 "frozen reference implementation through Phase 4.7 cutover" reframing below is dead. PF Runtime was archived to `_archive/2026/pf-runtime/`; Phase 4.7 was archived. Hermes Agent v0.12.0 is again the unmodified canonical runtime — no reframing, no cutover pending. The original ADR-001 decision (this doc) stands cleanly on its own. See `~/.claude/plans/here-is-what-we-joyful-torvalds.md` and the four 2026-05-18 ADRs for the post-pivot world.

> **Earlier amendment (ADR-006, 2026-05-06, now superseded):** Hermes v0.12.0 is reframed from "unified runtime" to "frozen reference implementation through Phase 4.7 cutover." This ADR's reasoning is correct for Phase 0 — Hermes gave us conventions (`SOUL.md` / `MEMORY.md` / `USER.md` / `CLAUDE.md`), the OpenClaw migrator (24 items migrated cleanly), and a working 13-profile cutover path. We keep all of those. ADR-006 commits to building **PrettyFly Runtime** at `~/Projects/agents/pf-runtime/` and replacing the runtime layer at Phase 4.7 (between LAIK-as-MCP fusion at 4.5 and gravity-claw retirement at 5). See `_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md` for full reasoning.

## Context

Four overlapping agentic projects (`mike-lawdbot`, `mission-control`, `gravity-claw`, `paperclip`) plus the shared OpenClaw runtime drift apart in conventions, none ship native versions of the 2026-standardized primitives (agentskills.io, MCP, A2A, dialectic memory, multi-channel gateway), and maintenance pulls time away from the PrettyFly OS marketplace strategy.

## Decision

Adopt **Hermes Agent (Nous Research, MIT, v0.12.0 as of 2026-04-30)** as the single agent runtime. Migrate all four projects into a 13-profile org chart inside this `~/Projects/agents/` monorepo. Productize the result as the PrettyFly OS marketplace (BYOK, three tiers, eight functional silos).

## Why Hermes specifically

1. **Native primitives** — agentskills.io / SKILL.md, MCP, A2A-ready, Honcho dialectic memory, 15-channel gateway, 6 terminal backends (local/Docker/SSH/Daytona/Singularity/Modal), profile isolation, prompt-cache discipline. We were building these by hand.
2. **First-class OpenClaw migrator** — `hermes claw migrate` reads `~/.openclaw/` and translates skills to the agentskills.io standard. Phase 0 dry-run shows 24 items migrate cleanly with 2 minor conflicts.
3. **Multi-agent v0.12.0 Kanban (2026-04-30)** — replaces Mission Control's homegrown coordination layer.
4. **VanClief framework alignment** — the folder-as-workspace / 3-layer routing thesis preached across his channel maps 1:1 onto Hermes' built-in conventions (`SOUL.md` / `MEMORY.md` / `USER.md` / `AGENTS.md` / `~/.hermes/skills/`).
5. **Council compliance** — `prettyfly-os-council-synthesis 2026-04-19` set WIP=3. This consolidation closes 3 active threads (gravity-claw, mission-control, paperclip-as-idle) and folds them into one. Net WIP delta: −2.

## Authoritative reasoning

`~/Projects/research-vault/research/2026-05-04-hermes-agent-unified-overhaul.md` (24,069 words, 53 sources, v1+v2 addendum).

## Surgical execution plan

`~/.claude/plans/before-we-start-make-ticklish-island.md` (Phases 0–6, 14-day shadow per money-flowing pipeline, 90-day archive bridge).

## Hard constraints (do not violate)

1. Money-flowing pipelines untouched until their named phase: ConsultOps Marc, sportsbook predictions, mike-lawdbot Telegram, YEH ops.
2. Paperclip stays on **Claude Max subscription**, never metered Anthropic API.
3. CARL per-project rule isolation preserved.
4. Langfuse trace volume ±5% before/after each cutover.
5. AGPL Honcho stays server-side only — never bundled into tenant deliverables.
6. Codex parallel-review-agent (`~/.agents/skills/staged-review/`, `~/.local/bin/closeout-stack`) is env-scope, untouched.
7. PrettyFly OS marketplace REUSES existing Supabase + Auth + RLS (ADR-007).

## Phase 0 evidence (2026-05-04)

- Hermes installed: `v0.12.0 (2026.4.30)` at `/Users/alexhale/.local/bin/hermes`.
- `hermes doctor`: green for Anthropic / OpenRouter / NVIDIA NIM / codex CLI / 89 bundled skills / all critical tool families. Mistral key in `~/.hermes/.env` (68 models).
- OpenClaw snapshot: `~/Projects/_archive/2026/openclaw-snapshot-phase0.tgz` (42.6 MB).
- Migration baseline SHAs: mike-lawdbot `d4624d0`, mission-control `d8efa2d`, gravity-claw `7c92bfe`. Paperclip has no `.git` — confirms lab-stage.
- `hermes claw migrate --dry-run`: **24 items migratable, 2 conflicts (soul/model-config), 25 inapplicable.** Migratable items: memory, user-profile, 14 individual skills (brainstorm-stack, close-day, cost-management, devils-advocate, dispatch, focus-interview, jr-dev, morning-brief, planning-awareness, project-registry, research-stack, session-lifecycle, supabase-patterns, upwork-arbitrage), antfarm-workflows shared-skill, agent-config (agent/compression/terminal blocks). Captured at `docs/phase0-claw-dry-run.log`.
- One environmental note: OpenClaw process running locally (PID 1073). Acceptable for dry-run; needs to stop before real migration in Phase 2.

## Two skills the dry-run wants to import that we will EXCLUDE

The dry-run flagged `personal-skills/rls-audit` and `personal-skills/staged-review` as candidates. These already live env-scope at `~/.agents/skills/{rls-audit,staged-review}/` per Hard Constraint #6 — they stay there, do not import into the Hermes profile tree.

## Status

Phase 0 complete. Awaiting Alex confirmation on the Phase 0 → Phase 1 transition and the 8 open decisions in plan §G.

## Consequences

- Four projects retire over 5–7 weeks; production never breaks (parallel-then-flip per money-flowing pipeline).
- PrettyFly OS marketplace gains a productizable agent fleet inside the existing app shell.
- VanClief AI-Expert profile (the 13th) becomes the continuous-improvement engine.
- Codex review-agent unchanged.
