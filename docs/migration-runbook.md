# Migration runbook — Hermes consolidation + Company AGI fusion

> **Status pointer:** Phase 0 done · Phase 1 foundation committed · Phase 1.5 in flight (Honcho laptop, Telegram pairing) · Phase 4.5 inserted between 4 and 5 (LAIK-as-MCP fusion).

## Phase index

| Phase   | Goal                                                                  | Money pipelines?                             | Estimated calendar                        | Status             |
| ------- | --------------------------------------------------------------------- | -------------------------------------------- | ----------------------------------------- | ------------------ |
| 0       | Probe + scaffold + dry-run                                            | No                                           | 1–2 days                                  | ✅ Done 2026-05-04 |
| 1       | Personal profile cutover (gravity-claw heir) + foundation             | No                                           | 3–5 days active + 14-day shadow           | 🟡 In flight       |
| 1.5     | Honcho stand up + Telegram pairing (deferred from Phase 1)            | No                                           | 1 day                                     | 🟡 In flight       |
| 2       | Mike-lawdbot migration via `hermes claw migrate` + BOT_TOKEN rotation | **Yes (Telegram)**                           | 2–3 days + 14-day shadow                  | ⬜ Not started     |
| 3       | Paperclip activation (Claude Max session, NOT metered)                | No                                           | 3–4 days                                  | ⬜ Not started     |
| 4       | Mission Control data migration + retirement                           | **Yes (ConsultOps Marc, sportsbook ingest)** | 5–7 days + 14-day shadow + 90-day archive | ⬜ Not started     |
| **4.5** | **LAIK-as-MCP fusion** (per Company AGI report §3.2)                  | **Yes (ConsultOps daily, YEH dry_run)**      | 5–7 days                                  | ⬜ Not started     |
| 5       | Gravity-claw retirement (Fly.io heartbeat off)                        | No                                           | 2–3 days                                  | ⬜ Not started     |
| 6       | OpenClaw retirement + PrettyFly OS branding + marketplace launch      | No (all migrated)                            | 1–2 weeks                                 | ⬜ Not started     |

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

## Phase 5 — gravity-claw retirement

Fly.io heartbeat: `flyctl scale count 0 --app gravity-claw-heartbeat`. Edit `.github/workflows/heartbeat.yml` → `on: workflow_dispatch:` only. Verify Fly.io billing $0 for 7 consecutive days. Stop primary app. Vercel paused. Repo tagged `retired-2026-XX-XX`, moved to `_archive/2026/`. MANIFEST updated.

## Phase 6 — OpenClaw retirement + marketplace launch

`ssh vps 'systemctl stop openclaw.service && systemctl disable openclaw.service'`. Archive `~/.openclaw/` for 90-day forensic window. PrettyFly OS branding ships. console.prettyflyforai.com/company-agi catalog goes live with three tiers (Lite $499 / Pro $1,999 / Scale $9,999) per Company AGI fusion §5.

## Phase pointer (current)

Edit this line as phases complete: **CURRENT PHASE: 1 + 1.5 (parallel)**.
