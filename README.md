# PrettyFly Hermes Org

> 12 + 1 agents, one repo. The unified home for every Hermes profile that runs Alex's agentic stack.

## What this is

The consolidator for [Hermes Agent](https://github.com/NousResearch/hermes-agent) profiles that replace four separate projects (`mike-lawdbot`, `mission-control`, `gravity-claw`, `paperclip`) plus the shared OpenClaw runtime. Versioned source-of-truth in `hermes/profiles/{name}/`; runtime mirrors live in `~/.hermes/profiles/{name}/`.

This repo is also the front door for the **PrettyFly OS marketplace** — a productized agent SKU catalog SMBs can install à la carte (BYOK pricing, three tiers, eight functional silos).

## Roster

The 13 profiles, organized into 4 squads:

| Squad                         | Profiles                                                      |
| ----------------------------- | ------------------------------------------------------------- |
| **Personal Operating System** | `personal`, `mobile`, `codex`                                 |
| **Money-Flowing Operations**  | `lawdbot`, `consultops`, `sportsbook`, `yeh-ops`              |
| **Brand & Growth**            | `atlas-ceo`, `viper-outreach`, `quill-content`, `forge-audit` |
| **Internal Platform**         | `ops` (ledger + cie + apex)                                   |
| **Meta**                      | `vanclief` (AI-Expert / fleet auditor)                        |

## Architecture

Hermes core (single agent, profile-isolated, MCP-native) + Honcho (dialectic memory) + agentskills.io (procedural memory) + Google A2A (inter-agent) + multi-provider router (Anthropic / Mistral / NVIDIA NIM / OpenRouter / Nous Portal).

See `docs/filesystem-spec.md`, `docs/memory-spec.md`, `docs/autonomy-spec.md`, `docs/marketplace-spec.md`.

## Status

Current phase: **Phase 0** complete (scaffold + Hermes v0.12.0 installed + OpenClaw dry-run captured). See `MANIFEST-fragment.md` and `_meta/decisions/2026-05-04-adopt-hermes.md`.

## Authoritative spec

Architectural reasoning (24,069 words, 53 sources) lives at:
`~/Projects/research-vault/research/2026-05-04-hermes-agent-unified-overhaul.md`

Surgical execution plan:
`~/.claude/plans/before-we-start-make-ticklish-island.md`
