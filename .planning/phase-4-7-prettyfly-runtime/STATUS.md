# Phase 4.7 status tracker

> **Last updated:** 2026-05-06 (aligned with [`PIVOT_2026-05-06.md`](PIVOT_2026-05-06.md)). Operator G0=YES locked. Phase 4.7.0 pre-work CLEARED. **G1 (7-night Hermes baseline) is superseded — do not schedule G1 work;** pivot ladder A→E is authoritative. Older notes below are retained for context.

## Pivot summary (authoritative)

- **Sequencing:** [`PIVOT_2026-05-06.md`](PIVOT_2026-05-06.md) §4 (sub-phases A–E) and §3 (replacement cutover gates).
- **Full charter:** [`PLAN.md`](PLAN.md) — where it conflicts with PIVOT §3–§4, **PIVOT wins**.
- **Personal Slack cutover:** [`CUTOVER_C_PLAYBOOK.md`](CUTOVER_C_PLAYBOOK.md).

| Pivot sub-phase              | Ships                        | Status                                                       |
| ---------------------------- | ---------------------------- | ------------------------------------------------------------ |
| **A** Loop + profile loader  | CLI `run_session` round-trip | Implemented in `pf-runtime/pf_runtime/`                      |
| **B** Memory tiers 1–2       | SoulReader + BufferStore     | Wired in gateway + loop                                      |
| **C** Slack + cutover        | Iris on PF Runtime           | Repo: channels + gateway + tests; operator steps in playbook |
| **D** Dream loop + tiers 3–4 | SkillRegistry + compaction   | Not started                                                  |
| **E** Kanban + shadow        | Postgres + fleet             | Not started                                                  |

## Post-4.7.0 swarm review findings (2026-05-06 15:30 — historical)

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

**Fix path**: operator copies provider key lines from `~/.hermes/.env` into `~/.hermes/profiles/personal/.env`, then `launchctl kickstart -k gui/$UID/ai.hermes.gateway-personal`. Repeat for other profiles in fleet scope. After PF Runtime cutover, the same per-profile `.env` pattern applies to the PF launchd job.

**Architecture note**: tenant isolation via per-profile `.env` is correct; add a bootstrap at profile-creation time (`§5.0e` candidate) so keys are not hand-copied.

## Gates

| Gate                          | Status                                                                                                            |
| ----------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| G0 marketplace GTM dependency | ✅ YES (operator 2026-05-06)                                                                                      |
| G1 Hermes baseline (7 nights) | ⏭️ **Superseded** by PIVOT — see PIVOT §3 for absolute Wilson / Ragas / real-job / latency / P0 gates             |
| G2 Hermes feature audit       | 🟡 **PARTIAL** — Phase 1 matrix done 2026-05-06; Phase 2 (SQLite + Langfuse tool evidence) conditional on traffic |

## Pre-work artifacts

| Item                            | Status                                                                                                            | Path                                                                                                    |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| A. LAIK MCP boundary spec       | ✅ written 2026-05-06                                                                                             | `mcp-servers/laik/SPEC.md`                                                                              |
| B. Profile-dir contract test    | ✅ written 2026-05-06                                                                                             | `tests/profile_dir_contract.py`                                                                         |
| C. Hermes commit-watcher        | ✅ written 2026-05-06                                                                                             | `scripts/hermes-commit-watcher.sh` + `~/Library/LaunchAgents/com.prettyfly.hermes-commit-watcher.plist` |
| D. G1 baseline measurement      | ⏭️ Superseded (pivot); keep `scripts/lib/` helpers for eval                                                       | (historical baseline dir optional)                                                                      |
| E. G2 feature audit             | 🟡 Phase 1 only (13/13 profile rows populated post-iteration-bug-fix); Phase 2 SQLite + Langfuse evidence pending | `.planning/phase-4-7-prettyfly-runtime/feature-usage/HERMES_FEATURE_USAGE.md`                           |
| F.1 PF Runtime SPEC.md          | ✅ written 2026-05-06                                                                                             | `pf-runtime/SPEC.md`                                                                                    |
| F.2 MEMORY_LIFECYCLE.md         | ✅ written 2026-05-06                                                                                             | `pf-runtime/docs/MEMORY_LIFECYCLE.md`                                                                   |
| F.3 SKILL_SELF_GEN_BOUNDS.md    | ✅ written 2026-05-06                                                                                             | `pf-runtime/docs/SKILL_SELF_GEN_BOUNDS.md`                                                              |
| F.4 ADAPTER_PLUGIN_INTERFACE.md | ✅ written 2026-05-06                                                                                             | `pf-runtime/docs/ADAPTER_PLUGIN_INTERFACE.md`                                                           |

## Sub-phase status (PIVOT ladder)

| Pivot | PLAN cross-ref           | Status                                     | Measured target (PIVOT §4)        |
| ----- | ------------------------ | ------------------------------------------ | --------------------------------- |
| **A** | loop + loader            | 🟢 in tree                                 | Non-empty assistant reply + trace |
| **B** | memory 1–2               | 🟢 in tree                                 | Buffer persistence tests          |
| **C** | Slack gateway (personal) | 🟡 repo + tests; operator cutover optional | 50 DMs / 24h, p95 ≤2s             |
| **D** | dream + tiers 3–4        | ⬜                                         | Dream firing + tier4 isolation    |
| **E** | Kanban + cutover         | ⬜                                         | Postgres p95 + 48h shadow         |

**Final cutover evaluation:** PIVOT §3 (Wilson, Ragas, real-job, latency/throughput, P0) — not the pre-pivot Hermes delta table in PLAN.md §11.

## Operator cutover (Sub-phase C)

After `pytest` / `ruff` / `mypy` pass in `pf-runtime/` (see [`CUTOVER_C_PLAYBOOK.md`](CUTOVER_C_PLAYBOOK.md)): foreground smoke `python -m pf_runtime gateway --profile personal`, then launchd swap; keep Hermes plist for rollback.

## Reference docs

- **Pivot:** `.planning/phase-4-7-prettyfly-runtime/PIVOT_2026-05-06.md`
- ADR-006: `_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md`
- Detailed plan: `.planning/phase-4-7-prettyfly-runtime/PLAN.md`
- CLAWS map: `pf-runtime/docs/CLAWS_ROLE_MAP.md`
- Research: `~/Projects/research-vault/research/2026-05-06-jack-roberts-thesis-bare-metal-hermes-replacement.md`
- Migration runbook: `docs/migration-runbook.md`
