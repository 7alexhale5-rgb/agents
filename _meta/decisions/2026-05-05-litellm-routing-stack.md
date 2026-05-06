---
adr: 005
title: LiteLLM routing stack for the 13-agent Hermes Slack fleet
date: 2026-05-05
status: accepted
supersedes: none
related:
  - 2026-05-04-adopt-hermes.md
  - 2026-05-05-slack-ecosystem-pivot.md
  - 2026-05-05-substrate-architecture.md
---

# ADR-005 — LiteLLM routing stack for the Hermes 13-agent fleet

## Context

Following the Slack ecosystem cutover (ADR-004), the prettyfly.ai Slack workspace runs 13 always-on Hermes agents (atlas-ceo, codex, consultops, forge-audit, lawdbot, mobile, ops, personal, quill-content, sportsbook, vanclief, viper-outreach, yeh-ops). Out of the box, every Hermes profile inherits `~/.hermes/config.yaml` `model.default = anthropic/claude-opus-4.6` — meaning all 13 agents would route to a frontier-priced model regardless of task, and there was no surgical mechanism to cap, monitor, or redirect spend per agent.

We need:

1. The right model on the right task — Opus 4.7 only where reasoning is the product
2. A single chokepoint for all LLM spend so cost can be measured, capped, and rerouted
3. Per-agent budgets (daily + monthly) with hard 429 enforcement
4. Failover when a provider rate-limits or errors
5. Prompt-cache compounding across providers
6. One observability pane that consolidates spend, latency, traces, and config

## Decision

Adopt **LiteLLM proxy** as the single LLM endpoint for the entire fleet, fronted by a **Postgres+Redis** docker-compose stack on the same Mac that runs Hermes. Each agent gets a virtual API key with its own budget. Hermes profiles point `OPENAI_API_BASE` at `http://127.0.0.1:4000` and request a tier name (`tier-premium`, `tier-standard`, `tier-cheap`, `tier-utility`, `tier-fast-quant`, `tier-free`, `tier-local`); LiteLLM resolves tier→primary→fallback chain.

Observability consolidates into a single Next.js dashboard, the **Fleet Console**, extending the existing `~/Projects/mission-control/api-cost-dashboard/` rather than building a parallel app.

### Tier mapping

| Tier              | Primary                             | Fallback chain                                      |
| ----------------- | ----------------------------------- | --------------------------------------------------- |
| `tier-premium`    | `claude-opus-4-7` (1h cache)        | sonnet-4-6 → gemini-2.5-pro                         |
| `tier-standard`   | `claude-sonnet-4-6` (5min cache)    | deepseek-v4-pro → gemini-2.5-pro                    |
| `tier-utility`    | `claude-haiku-4-5`                  | gemini-2.5-flash → mistral-small-3                  |
| `tier-cheap`      | `gemini-2.5-flash`                  | haiku-4-5 → mistral-small-3                         |
| `tier-fast-quant` | `cerebras/llama-4-70b` (~3000 t/s)  | nvidia/llama-3.3-70b → openrouter/deepseek-v4-flash |
| `tier-free`       | `openrouter/qwen-3.6-plus:free`     | gemini-2.5-flash → ollama/qwen-3-35b-a3b            |
| `tier-local`      | `ollama/qwen-3-35b-a3b` (Apple MLX) | openrouter/qwen-3.6-plus:free → gemini-2.5-flash    |

### Per-agent placement and budgets

| Agent          | Tier       | Monthly cap | Daily cap | RPM | Role                      |
| -------------- | ---------- | ----------- | --------- | --- | ------------------------- |
| atlas-ceo      | premium    | $20         | $1        | 30  | CEO strategy, OKR roll-up |
| forge-audit    | premium    | $15         | $0.75     | 20  | Audit/review              |
| codex          | standard   | $10         | $0.50     | 60  | Coding                    |
| quill-content  | standard   | $5          | $0.25     | 30  | Content/writing           |
| consultops     | standard   | $5          | $0.25     | 60  | Sales ops                 |
| lawdbot        | standard   | $5          | $0.25     | 60  | Legal-adjacent            |
| yeh-ops        | standard   | $5          | $0.25     | 60  | YEH project ops           |
| personal       | cheap      | $2          | $0.15     | 60  | Mixed-domain              |
| ops            | utility    | $1          | $0.10     | 120 | Glue work                 |
| mobile         | cheap      | $1          | $0.10     | 60  | Quick replies             |
| viper-outreach | cheap      | $0.50       | $0.05     | 60  | Templated outreach        |
| sportsbook     | fast-quant | $2          | $0.15     | 30  | Latency quant             |
| vanclief       | free       | $0 (hard)   | $0        | 30  | Read-only oracle          |
| **Total**      |            | **$71.50**  |           |     |                           |

Anthropic share ≈ $60/mo, sitting under the $75 console hard cap.

### Components

| #   | What                             | Where                                                                         |
| --- | -------------------------------- | ----------------------------------------------------------------------------- |
| 1   | LiteLLM proxy + Postgres + Redis | docker-compose at `~/.hermes/litellm/`, bound to 127.0.0.1:4000               |
| 2   | Hermes profile config            | each `~/.hermes/profiles/<slug>/.env` + `config.yaml` rewired                 |
| 3   | Per-agent virtual keys           | seeded by `~/.hermes/litellm/scripts/seed-keys.sh` against agents.json        |
| 4   | Fleet Console (dashboard)        | `~/Projects/mission-control/api-cost-dashboard/` extended in place, port 3400 |
| 5   | Alerting                         | Slack webhook into `ops` profile + LiteLLM threshold callbacks at 50/80/100%  |
| 6   | Fleet CLI                        | `~/.local/bin/fleet` mirrors dashboard mutations for terminal users           |

## Why LiteLLM, not Portkey or OpenRouter alone

| Need                                     | LiteLLM             | Portkey     | OpenRouter          |
| ---------------------------------------- | ------------------- | ----------- | ------------------- |
| Self-host (no per-log fee)               | ✓                   | ✗ ($36/mo+) | ✗ (5.5% credit fee) |
| Per-key budget caps                      | ✓ (Postgres-backed) | ✓           | ✗                   |
| Cross-provider prompt-cache pass-through | ✓ via Redis         | ✓           | partial             |
| Fallback chains                          | ✓                   | ✓           | model-string only   |
| Free for 13-key fleet                    | ✓                   | ✗           | ✗                   |
| Local Ollama upstream                    | ✓                   | partial     | ✗                   |

LiteLLM is open-source, self-hosted, free at this scale, and the only option that lets us make Ollama (running on the same Mac) a peer upstream to Anthropic/Gemini/Cerebras.

OpenRouter remains an _upstream_ of LiteLLM (primarily for free Qwen 3.6-Plus and DeepSeek V4) rather than the gateway itself.

## Why Mac, not VPS

Hermes gateways run on the Mac. Putting LiteLLM on the same machine eliminates a network hop, removes a TLS surface, and lets local Ollama be a first-class upstream. The Fleet Console _mirror_ runs on the VPS for read-only public access at `fleet.prettyflyforai.com`; the source-of-truth LiteLLM and SQLite spend log live on the Mac.

## Surgical control surface

| Knob                       | API                                                             |
| -------------------------- | --------------------------------------------------------------- |
| Per-key daily cap          | `POST /key/update {max_budget_per_day}`                         |
| Per-key monthly cap        | `POST /key/update {max_budget}`                                 |
| Tier substitution          | edit `model_group_alias` and `POST /config/reload`              |
| Provider kill              | `model_list[].metadata.disabled=true`, reload                   |
| Anthropic Console hard cap | $75/mo set in dashboard — final API-level safety net            |
| Budget alerts              | LiteLLM `slack_alerting.alerting_threshold` at 30% / 80% / 100% |

## Consequences

**Wins**

- Single chokepoint = single bill we can reason about
- Per-agent budgets enforced at the API layer (not just monitoring)
- Tier swaps are configuration, not code — no Hermes restart needed
- Local Ollama becomes a first-class fallback for free-tier overflow

**Costs**

- New runtime dependency on Docker Desktop (already installed)
- Three additional containers running 24/7 on the Mac (~250 MB RAM total)
- One additional secret rotation surface (LiteLLM master + salt keys)

**Risks accepted**

- LiteLLM admin API surface — secured by master key + localhost-only binding + UI behind auth
- Postgres data is local-only — backed up via macOS Time Machine, not separately replicated
- A network partition between Mac and the VPS (Tailscale) means the public mirror goes stale; the Mac dashboard remains live

## Calibration plan

Week 1 — observe. Watch the Fleet Console daily; do not edit budgets. Goal is to learn each agent's actual usage shape (peak hours, avg tokens/turn, cache hit rate).

Week 2 — adjust. Set caps to actual_p95 × 1.5. Promote any agent that hits its tier ceiling repeatedly. Demote any agent that consistently uses < 30% of cap.

Week 4 — review. ADR addendum captures lessons + any tier reshuffles.

## Rollback

Stop LiteLLM stack: `cd ~/.hermes/litellm && docker compose down`.
Restore each profile's `.env` from the `.bak` file written at Phase 2 start.
Hermes profiles fall back to direct Anthropic/Gemini/etc. via existing keys.

## Decision lineage

- Research brief: `~/Projects/research-vault/research/2026-05-05-hermes-13-agent-tokenmaxx-routing.md`
- Tokenmaxx wireframe + addendum: this conversation, 2026-05-05
- User confirmation: $100/mo budget OK · LiteLLM on Mac · Anthropic cap $75 · Hybrid dashboard · Mobile in backlog
