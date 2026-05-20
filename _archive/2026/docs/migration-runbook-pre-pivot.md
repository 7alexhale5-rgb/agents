# Migration runbook — Hermes consolidation + Company AGI fusion

> **Status pointer:** Phase 0 done · Phase 1 foundation committed · Phase 1.5 in flight (Honcho laptop, Slack pairing per ADR-004) · Phase 4.5 inserted between 4 and 5 (LAIK-as-MCP fusion) · **Phase 4.7 inserted between 4.5 and 5 (PrettyFly Runtime bare-metal cutover, per ADR-006).**

## Phase index

| Phase   | Goal                                                                                                                                                                                                                                                                                                                                                           | Money pipelines?                             | Estimated calendar                                  | Status                                                                                                                                                                                                  |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0       | Probe + scaffold + dry-run                                                                                                                                                                                                                                                                                                                                     | No                                           | 1–2 days                                            | ✅ Done 2026-05-04                                                                                                                                                                                      |
| 1       | Personal profile cutover (gravity-claw heir) + foundation                                                                                                                                                                                                                                                                                                      | No                                           | 3–5 days active + 14-day shadow                     | 🟡 In flight                                                                                                                                                                                            |
| 1.5     | Honcho stand up + Slack ecosystem pairing (per ADR-004)                                                                                                                                                                                                                                                                                                        | No                                           | 1 day                                               | 🟡 In flight                                                                                                                                                                                            |
| 2       | Mike-lawdbot migration via `hermes claw migrate` + BOT_TOKEN rotation                                                                                                                                                                                                                                                                                          | **Yes (Telegram)**                           | 2–3 days + 14-day shadow                            | ⬜ Not started                                                                                                                                                                                          |
| 3       | Paperclip activation (Claude Max session, NOT metered)                                                                                                                                                                                                                                                                                                         | No                                           | 3–4 days                                            | ⬜ Not started                                                                                                                                                                                          |
| 4       | Mission Control data migration + retirement                                                                                                                                                                                                                                                                                                                    | **Yes (ConsultOps Marc, sportsbook ingest)** | 5–7 days + 14-day shadow + 90-day archive           | ⬜ Not started                                                                                                                                                                                          |
| **4.5** | **LAIK-as-MCP fusion** (per Company AGI report §3.2)                                                                                                                                                                                                                                                                                                           | **Yes (ConsultOps daily, YEH dry_run)**      | 5–7 days                                            | ⬜ Not started                                                                                                                                                                                          |
| **4.7** | **PrettyFly Runtime bare-metal** (per ADR-006 + **[`PIVOT_2026-05-06.md`](../.planning/phase-4-7-prettyfly-runtime/PIVOT_2026-05-06.md)**) — sub-phases **A–E**: loop+loader → memory 1–2 → Slack cutover (personal) → dream+tier3–4 → Kanban+shadow. G1 Hermes baseline **skipped** per pivot; cutover gates are absolute (Wilson/Ragas/real-job/latency/P0). | **Yes (13 profiles at end state)**           | ~25–40 focused hours + soak windows + 14-day shadow | 🟡 **In flight** — A/B in repo; **C** Slack gateway; operator playbook: [`.planning/phase-4-7-prettyfly-runtime/CUTOVER_C_PLAYBOOK.md`](../.planning/phase-4-7-prettyfly-runtime/CUTOVER_C_PLAYBOOK.md) |
| 5       | Gravity-claw retirement (Fly.io heartbeat off)                                                                                                                                                                                                                                                                                                                 | No                                           | 2–3 days                                            | ⬜ Not started                                                                                                                                                                                          |
| 6       | OpenClaw retirement + PrettyFly OS branding + marketplace launch                                                                                                                                                                                                                                                                                               | No (all migrated)                            | 1–2 weeks                                           | ⬜ Not started                                                                                                                                                                                          |

> **Hermes pin (per ADR-006):** v0.12.0 (2026.4.30). Do not run `hermes update`. Subscribe to releases for security-fix porting only. Hermes is reframed from "unified runtime" to "frozen reference implementation through Phase 4.7 cutover." All Phase 1–4.5 work runs on this pin.

## Authoritative specs

- Architecture v1+v2: `~/Projects/research-vault/research/2026-05-04-hermes-agent-unified-overhaul.md` (24,069 words)
- Company AGI fusion: `~/Projects/research-vault/research/2026-05-04-company-agi-laik-hermes-fusion.md` (6,350 words)
- Surgical plan: `~/.claude/plans/before-we-start-make-ticklish-island.md`

This runbook is the operator's view. Read those specs for the why.

## Phase 0 — completed 2026-05-04

Hermes v0.12.0 installed. Dry-run captured at `docs/phase0-claw-dry-run.log` (24 migratable / 2 conflicts / 25 N/A). Repo scaffolded. ADR-001 written. MANIFEST updated with `agents` row + migration phase notes on the four retiring projects.

## Phase 1 — personal profile cutover (in flight)

Acceptance: 7 consecutive days of voice replies referencing yesterday's conversation correctly via Hermes session DB recall, zero cross-talk vs gravity-claw transcript baseline.

Steps committed today (commit `0462724`):

- Personal profile SOUL/USER/MEMORY/CLAUDE/manifest/pricing/config (versioned)
- Layer-2 rooms: voice / daily-digest / obsidian-sync (CONTEXT.md each)
- voice-loop skill (Groq Whisper Turbo + Google TTS)
- 4d-senses MCP server (smoke-tested green: 5 tools, status call returns JSON)
- Scripts: sync-profile.sh / bootstrap-profile.sh / seal-profile.sh
- Email-triage SKU (full marketplace package)

Steps remaining:

- Phase 1.5 (below) — Honcho + Telegram
- Run `scripts/sync-profile.sh push personal` to mirror versioned tree → `~/.hermes/profiles/personal/`
- Pair the new Telegram bot
- Smoke voice exchange
- 14-day shadow window starts on first real voice exchange

## Phase 1.5 — Honcho self-host + Telegram pairing (in flight)

### Honcho laptop stand-up

```bash
cd ~/Projects/agents/honcho
cp .env.template .env
# Generate secrets:
openssl rand -hex 32  # → HONCHO_DB_PASSWORD
openssl rand -hex 32  # → HONCHO_JWT_SECRET
# Edit .env, paste secrets + Anthropic + OpenAI keys

# Start Docker Desktop first (currently not running — gates this step)
open -a Docker

# Wait ~30s for daemon, then:
docker compose up -d
docker compose logs -f honcho-api  # wait for "Application startup complete"
curl -fsS http://localhost:8765/health  # smoke test
```

Acceptance: `curl http://localhost:8765/health` returns 200. Honcho API up at `localhost:8765`, DB on `localhost:8764` (loopback only).

### Telegram pairing

```bash
# 1. Talk to @BotFather on Telegram, /newbot, get a token (do NOT paste into a chat)
# 2. Run the pairing script
~/Projects/agents/scripts/pair-telegram.sh personal <bot-token-from-botfather>
# 3. Smoke test
hermes profile use personal
hermes channel test telegram
```

Acceptance: send a "/start" to the new bot, agent responds with the pairing-confirmation message.

## Phase 2 — mike-lawdbot migration

`hermes claw migrate --workspace ~/Projects/mike-lawdbot/openclaw/workspace --target ~/.hermes/profiles/lawdbot/` (after Phase 0 dry-run review).

**BOT_TOKEN rotation procedure** (cutover day, end of 14-day shadow):

1. During shadow: pair Hermes-lawdbot to a temporary second bot (`@MikeLawdbot2_dev`).
2. On flip day: in @BotFather, `/revoke` the production Mike bot token, generate fresh.
3. `hermes channel update telegram --profile lawdbot --token $ROTATED_TOKEN && hermes profile restart lawdbot`.
4. `ssh vps 'systemctl stop openclaw.service'` (do NOT delete; warm fallback for 14 more days).
5. Rotated token never returns to OpenClaw.

Skip the two skills the dry-run wants to import: `personal-skills/rls-audit` and `personal-skills/staged-review`. Those stay env-scope at `~/.agents/skills/` per Hard Constraint #6.

## Phase 3 — paperclip activation

Five separate profiles: `paperclip-atlas`, `paperclip-viper`, `paperclip-quill`, `paperclip-forge`, `paperclip-radar`. Each `config.yaml` MUST set:

```yaml
model:
  provider: claude-max-subscription
  channel: oauth-session
  fallback: none
```

Verify with `hermes model probe --profile paperclip-atlas` — must report `provider=claude-max-subscription`, NOT `anthropic-api`.

## Phase 4 — Mission Control retirement

Honcho on VPS port 8766. Hybrid data preservation: `observations` table → Honcho via bulk import; `crm_leads`/`approval_queue`/`cost_ledger`/`shared_context` → stay in Postgres, exposed via readonly MCP `mission-control-archive` for 90 days.

Verify Langfuse trace volume ±5% before MC service stop.

## Phase 4.5 — LAIK-as-MCP fusion (NEW)

**Inserted between MC retirement and gravity-claw retirement per Company AGI fusion report §3.2.**

Goal: strip LAIK's FastAPI wrapper into a Python MCP server (`mcp-servers/laik/`) that exposes `laik_query`, `laik_sql`, `laik_propose_mutation`, `laik_confirm_mutation`, `laik_list_tenants`, `laik_status` to every Hermes profile.

Steps:

1. Build `mcp-servers/laik/` Python MCP server importing `kit.retrieval.pipeline` + `kit.orchestrator.tools` from the existing LAIK codebase.
2. Smoke test against ConsultOps tenant locally.
3. Register `laik` in shared-skills catalog so any profile can install it.
4. Update `personal/config.yaml` to attach `laik` MCP — first profile to consume.
5. Update `consultops/config.yaml` and `yeh-ops/config.yaml` similarly.
6. Move existing LAIK FastAPI service to read-only mode for 30-day overlap.
7. After 30 days of zero traffic to old FastAPI, decommission.

Acceptance: every Hermes profile that needs grounded company facts reads them through `laik_query()` or `laik_sql()` instead of Postgres-direct.

## Phase 4.7 — PrettyFly Runtime bare-metal (ADR-006 + pivot)

**Authoritative sequencing:** `.planning/phase-4-7-prettyfly-runtime/PIVOT_2026-05-06.md` (locked 2026-05-06). The pivot **supersedes** PLAN.md §1 G1 (7-night Hermes baseline before loop work). Status tracker: `.planning/phase-4-7-prettyfly-runtime/STATUS.md`.

**Sub-phases A–E (PIVOT §4):**

| Sub-phase | Delivers                                              | Gate (high level)                |
| --------- | ----------------------------------------------------- | -------------------------------- |
| **A**     | CLI + `run_session()` real reply                      | Trace + `finish_reason=stop`     |
| **B**     | Memory tiers 1–2 in loop                              | Buffer tests                     |
| **C**     | Slack Socket Mode for `personal` (Iris on PF Runtime) | 50 DMs/24h; see CUTOVER playbook |
| **D**     | Dream loop + tiers 3–4                                | Soak + bounds                    |
| **E**     | Postgres Kanban + 48h personal shadow                 | Load + P0                        |

**Final cutover gates (PIVOT §3):** (1) Wilson lower-CI ≥0.80 per profile (2) Ragas answer_relevance ≥0.83 personal golden set N=150 (3) real-job execution per profile in shadow (4) latency/throughput thresholds (5) zero P0.

**Operator procedure for personal Slack swap:** `.planning/phase-4-7-prettyfly-runtime/CUTOVER_C_PLAYBOOK.md`

### Historical PLAN.md detail (sub-phases 4.7.1–4.7.5)

The following bullets match the pre-pivot charter in `.planning/phase-4-7-prettyfly-runtime/PLAN.md` for file-level depth; **PIVOT wins** on sequencing and gates.

### Sub-phase 4.7.1 — Loop primitive (PLAN reference)

Build `pf-runtime/runtime/{loop,model_adapter,tool_dispatch,stop_condition,audit}.py`. Run the `personal` profile through one Slack DM round-trip via the LiteLLM proxy at `http://127.0.0.1:4000`. **Gate:** same prompt → same tool calls → ≤ 5% token delta vs Hermes baseline on the 30-question golden set.

### Sub-phase 4.7.2 — Memory + skills

Build the 4-tier memory stack (SOUL.md / rolling buffer in SQLite / episodic via LAIK MCP from Phase 4.5 / agentskills.io skill loader) plus skill self-generation (auto-author after 5+ tool calls) and the dream loop (post-session reflection that prunes contradictions into MEMORY.md). **Gate:** Ragas faithfulness ≥ 0.85 on the golden set; ≥ 1 skill auto-authored after a 5+ tool-call session; dream loop produces a non-empty post-session pruning diff.

### Sub-phase 4.7.3 — Channel gateway

Slack adapter first (Socket Mode + 13 OAuth-scoped apps from ADR-004), then Telegram, Email, Discord, optional voice via `file_shared`. **Gate:** identical action across runtimes for a 50-message corpus on `atlas-ceo`; money-pipeline OAuth scopes still read-only on `vanclief` and `sportsbook` (no `chat:write`/`im:write`/`reactions:write`/`files:write`).

### Sub-phase 4.7.4 — Kanban + Fleet Console

**Postgres-backed** task board (sibling schema in mission-control's existing Neon Postgres; revised from the original SQLite spec per architecture-finding-3 + concurrency-finding-A in PLAN.md §5/§10) + REST/WebSocket API + Fleet Console extension at `~/Projects/mission-control/api-cost-dashboard/` (extending ADR-005's dashboard, not building parallel). Tier 2 memory buffer remains SQLite per MEMORY_LIFECYCLE.md; only Kanban moves to Postgres. 14-day parallel shadow of all 13 profiles on PF Runtime alongside Hermes. **Gate:** trace volume ±5%, p95 latency ≤150% of baseline, concurrent throughput ≥80% of baseline, zero P0 incidents, per-profile real-job execution.

### Sub-phase 4.7.5 — Cutover (PLAN reference — gates superseded)

**Post-pivot canonical gates:** PIVOT §3 (Wilson ≥0.80, Ragas ≥0.83, real-job, latency/throughput, P0). The list below is the **pre-pivot** PLAN.md §11 text kept for file-layout history.

Operator decision against the five gates (historical PLAN.md §11 wording):

1. **Promptfoo Wilson lower-CI ≥ 85% per profile** on the existing `email-triage-eval-nightly` golden set; per-profile failures are not averaged.
2. **Ragas faithfulness ≥ Hermes baseline – 0.02** on personal profile golden set.
3. **Per-profile real-job execution gate** — every profile completes ≥1 full real-world job through PF Runtime during shadow (ConsultOps Marc lead intake, sportsbook predictions, lawdbot Telegram message, YEH-ops daily check-in, etc.); Sentry + Langfuse trace each end-to-end with zero P0.
4. **Latency + throughput gate** — p95 latency ≤150% of Hermes baseline; concurrent throughput ≥80% of baseline. Replaces the original backward-looking cost ±10% gate per skeptic-finding-4.
5. **Zero P0 incidents** across the full 14-day shadow (Sentry-defined P0 = production data loss, security breach, or ≥1 hour outage of a money-pipeline profile).

If all five pass: stop the Hermes service, flip profile dirs from `~/.hermes/profiles/` mirror to canonical at `pf-runtime/runtime-state/profiles/`, archive `~/.hermes/hermes-agent/` for 90-day forensic window. If any gate fails: stay on Hermes, document gaps in a follow-up ADR.

### Pre-work that fires now (parallel with Phase 1)

- `pf-runtime/SPEC.md` — runtime surface contract (profile loader, channel ABC, tool protocol, memory tier interfaces, kanban schema). ~1 day.
- LAIK MCP boundary lock — confirm Phase 4.5's MCP surface is runtime-agnostic before it ships. ~2 hours.
- `tests/profile_dir_contract.py` — nightly assertion that all 13 profile dirs are loadable by Hermes today and the PF Runtime spec. ~3 hours.
- Hermes commit-watcher — daily diff of HEAD..origin/main mailed to `forge-audit`. ~30 minutes.

## Phase 5 — gravity-claw retirement

Fly.io heartbeat: `flyctl scale count 0 --app gravity-claw-heartbeat`. Edit `.github/workflows/heartbeat.yml` → `on: workflow_dispatch:` only. Verify Fly.io billing $0 for 7 consecutive days. Stop primary app. Vercel paused. Repo tagged `retired-2026-XX-XX`, moved to `_archive/2026/`. MANIFEST updated.

## Phase 6 — OpenClaw retirement + marketplace launch

`ssh vps 'systemctl stop openclaw.service && systemctl disable openclaw.service'`. Archive `~/.openclaw/` for 90-day forensic window. PrettyFly OS branding ships. console.prettyflyforai.com/company-agi catalog goes live with three tiers (Lite $499 / Pro $1,999 / Scale $9,999) per Company AGI fusion §5.

## Phase pointer (current)

Edit this line as phases complete: **CURRENT PHASE: 1 + 1.5 (parallel) · Phase 4.7 pivot A–C in flight (`pf-runtime/` Slack gateway); see STATUS.md**.
