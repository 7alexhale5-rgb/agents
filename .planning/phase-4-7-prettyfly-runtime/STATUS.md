# Phase 4.7 status tracker

> **Last updated:** 2026-05-06 PM (post 5-agent swarm review of NEXT_PHASE_PLAN.md). Operator G0=YES locked. Phase 4.7.0 gate CLEARED. Plan amendment landed at `~/.claude/plans/lovely-cooking-flame.md`. **§5.5 read-only schema audit complete — see "G2 Phase 2 evidence path" row below.**

## Post-4.7.0 swarm review findings (2026-05-06 15:30)

- **§1.0 OVERTURNED**: personal gateway is now running on Slack as @iris (PID 36297, started 15:15 today via launchd `ai.hermes.gateway-personal`). active_profile flipped from atlas-ceo to personal. Phase 1 has technically started ~90 min ago but **has produced ZERO sessions** in `personal/state.db` — the launchd-started gateway is up but no round-trip has happened yet.
- **Channel correction**: personal profile is Slack-only (`channels.telegram.enabled: false` in config.yaml); Telegram deferred until a NEW bot token is paired. Original plan's "Telegram round-trip" verification step targets a platform that isn't wired.
- **Provider config**: personal/config.yaml uses `default_provider: openrouter` (model `nvidia/nemotron-nano-9b-v2`) + Anthropic for reasoning/strategic tiers. **Personal does NOT route through LiteLLM** — §5.0c Docker bring-up is not blocking for §5.0a verification.
- **gravity-claw comparator does not exist**: gravity_claw.db has 2 conversations total (2026-02-22 test pair) and 71 processed_updates that never persisted to the conversations table. Last activity 2026-04-16. Qdrant unreachable. Cross-day-recall acceptance redefined as Hermes-vs-Hermes (today's reply references content from a previous-day Hermes session in the same `state.db`) — this is what 4.7.5 cutover actually needs to measure.
- **Auth-fail observation**: 5 of 6 atlas-ceo Slack sessions yesterday returned `Provider authentication failed: No inference provider configured`. atlas-ceo's config lacks the provider stanza personal has. Personal SHOULD reply correctly when DM'd, but the operator should verify before the night-1 clock starts.

## G2 Phase 2 evidence path (2026-05-06 §5.5 audit)

State storage layout confirmed via read-only SQL probes:

| DB path                                 | Tables                                                      | Sessions count | Messages count | Notes                                                                                                                |
| --------------------------------------- | ----------------------------------------------------------- | -------------- | -------------- | -------------------------------------------------------------------------------------------------------------------- |
| `~/.hermes/state.db` (root)             | sessions, messages, schema_version, state_meta, FTS indexes | 0              | 0              | Empty — root is currently unused; per-profile DBs hold all data                                                      |
| `~/.hermes/profiles/personal/state.db`  | same shape                                                  | 0              | 0              | Gateway running since 15:15 but zero traffic — §5.0a operator action required                                        |
| `~/.hermes/profiles/atlas-ceo/state.db` | same shape                                                  | 6              | 5              | All 6 sessions from `source=slack` 2026-05-05 22:00–22:09 UTC; 5 have `api_call_count=0` (LiteLLM offline yesterday) |

Sessions schema columns confirmed: `id, source, started_at, ended_at, message_count, tool_call_count, input_tokens, output_tokens, estimated_cost_usd, actual_cost_usd, api_call_count, billing_provider, billing_mode, ...`. Messages schema columns: `id, session_id, role, content, tool_call_id, tool_calls, tool_name, **timestamp**, token_count, ...`. **Note**: messages uses `timestamp` not `created_at`; eval-audit pseudocode's `state.db.sessions` access pattern via `started_at` is correct.

G2 Phase 2 outcome: **session DBs exist with usable schema**. SQLite query path proceeds once real traffic accumulates. Schema works as expected — no schema drift, no path drift.

### §5.0a/c update (2026-05-06 16:55 ET)

After alex DM'd `@iris` and the pairing was approved (`hermes pairing approve slack WUT7UCGQ`), the second DM produced the first real session row in `personal/state.db` (`20260506_165222_f4257329`, 3 messages). The reply was the auth-fail path — not a real LLM-generated answer — because **the gateway's process env does not have OPENROUTER_API_KEY**.

**Root cause**: `~/Library/LaunchAgents/ai.hermes.gateway-personal.plist` exposes PATH/VIRTUAL_ENV/HERMES_HOME but does not source `~/.hermes/.env`. Because `HERMES_HOME` points to `~/.hermes/profiles/personal/`, Hermes loads `~/.hermes/profiles/personal/.env` for provider keys — which is a 2-line stub.

**Fleet-wide audit (Python, no shell pipe)**: all 13 profile `.env` files are 2-line stubs with no `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `GROQ_API_KEY`, `MISTRAL_API_KEY`, or `OPENAI_API_KEY` lines:

```
atlas-ceo, codex, consultops, forge-audit, lawdbot, mobile, ops, personal,
quill-content, sportsbook, vanclief, viper-outreach, yeh-ops
```

The global `~/.hermes/.env` has the keys. They never reached the per-profile env files.

**Fix path**: operator runs (Claude blocked by credential hook) — copies the 4-5 provider key lines from `~/.hermes/.env` into `~/.hermes/profiles/personal/.env`, then `launchctl kickstart -k gui/$UID/ai.hermes.gateway-personal`. Same pattern follows for the other 12 profiles when they're brought into Phase 1+ scope, but is NOT blocking for G1 (which only needs `personal-baseline`).

**Architecture note for plan amendment**: the per-profile `.env` design is good for tenant isolation (matches the THREAT_MODEL §"trust boundaries" surface), but the bootstrap process needs a script that initializes per-profile keys at profile-creation time. Add as `§5.0e` candidate task — not blocking G1, but the fleet won't rotate cleanly without it.

## Gates

| Gate                          | Status                                                                                                                                                                                                                                                                                                                                                                                         | Owner                 | Calendar                   | Output                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | -------------------------- | ----------------------------------------------------------------------------- |
| G0 marketplace GTM dependency | ✅ YES (operator confirmed 2026-05-06)                                                                                                                                                                                                                                                                                                                                                         | alex                  | —                          | This file                                                                     |
| G1 Hermes baseline (7 nights) | 🟡 starting tonight in dedicated `personal-baseline/` shadow workspace (per PLAN.md §1 G1 clarification)                                                                                                                                                                                                                                                                                       | PF Runtime build lead | 7 days                     | `.planning/phase-4-7-prettyfly-runtime/baseline/HERMES_BASELINE.md`           |
| G2 Hermes feature audit       | 🟡 **PARTIAL** — Phase 1 (config-grep + skills/ + rooms/voice/) ran 2026-05-06 across all 13 profile dirs. Phase 2 (SQLite session DB tool-call counts + Langfuse trace 80th-percentile-used tools over 30 days, per PLAN.md §1 G2) **deferred** — feature-scoping decisions for sub-phase 4.7.2 stay blocked on Phase 2 evidence; static enablement matrix is sufficient for sequencing only. | PF Runtime build lead | 1 day Phase 2 work pending | `.planning/phase-4-7-prettyfly-runtime/feature-usage/HERMES_FEATURE_USAGE.md` |

## Pre-work artifacts

| Item                            | Status                                                                                                            | Path                                                                                                    |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| A. LAIK MCP boundary spec       | ✅ written 2026-05-06                                                                                             | `mcp-servers/laik/SPEC.md`                                                                              |
| B. Profile-dir contract test    | ✅ written 2026-05-06                                                                                             | `tests/profile_dir_contract.py`                                                                         |
| C. Hermes commit-watcher        | ✅ written 2026-05-06                                                                                             | `scripts/hermes-commit-watcher.sh` + `~/Library/LaunchAgents/com.prettyfly.hermes-commit-watcher.plist` |
| D. G1 baseline measurement      | 🟡 starting                                                                                                       | `.planning/phase-4-7-prettyfly-runtime/baseline/HERMES_BASELINE.md`                                     |
| E. G2 feature audit             | 🟡 Phase 1 only (13/13 profile rows populated post-iteration-bug-fix); Phase 2 SQLite + Langfuse evidence pending | `.planning/phase-4-7-prettyfly-runtime/feature-usage/HERMES_FEATURE_USAGE.md`                           |
| F.1 PF Runtime SPEC.md          | ✅ written 2026-05-06                                                                                             | `pf-runtime/SPEC.md`                                                                                    |
| F.2 MEMORY_LIFECYCLE.md         | ✅ written 2026-05-06                                                                                             | `pf-runtime/docs/MEMORY_LIFECYCLE.md`                                                                   |
| F.3 SKILL_SELF_GEN_BOUNDS.md    | ✅ written 2026-05-06                                                                                             | `pf-runtime/docs/SKILL_SELF_GEN_BOUNDS.md`                                                              |
| F.4 ADAPTER_PLUGIN_INTERFACE.md | ✅ written 2026-05-06                                                                                             | `pf-runtime/docs/ADAPTER_PLUGIN_INTERFACE.md`                                                           |

## Sub-phase status

| Sub-phase                    | Status                   | Gate                                                                                             |
| ---------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------ |
| 4.7.0 pre-work               | ✅ CLEARED 2026-05-06    | All artifacts shipped + Codex re-review 0 critical (criterion ≤2) — 2 high + 1 low fixed in-pass |
| 4.7.1 loop primitive         | ⬜ blocked on G1 + 4.7.0 | Token delta ≤5% vs Hermes baseline                                                               |
| 4.7.2 memory + skills        | ⬜ blocked on 4.7.1      | Ragas ≥ baseline−0.02                                                                            |
| 4.7.3 channel gateway        | ⬜ blocked on 4.7.2      | 50/50 Slack parity on atlas-ceo                                                                  |
| 4.7.4 Kanban + Fleet Console | ⬜ blocked on 4.7.3      | SQL load test + 14d shadow                                                                       |
| 4.7.5 cutover                | ⬜ blocked on 4.7.4      | 5-gate evaluation                                                                                |

## Reference docs

- ADR-006: `_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md`
- Detailed plan: `.planning/phase-4-7-prettyfly-runtime/PLAN.md`
- Research backing: `~/Projects/research-vault/research/2026-05-06-jack-roberts-thesis-bare-metal-hermes-replacement.md`
- Migration runbook: `docs/migration-runbook.md`
