# CLAUDE.md — `~/Projects/agents/`

> **Status:** active | **Type:** tooling | **Phase:** 0 complete

You've opened the consolidated Hermes monorepo. This file is the Layer-1 router (per JEVanClief's folder-as-workspace pattern). Use it to decide which profile to descend into.

## Layer-1 routing — descend into the right profile

| Task                                               | Descend to                                 |
| -------------------------------------------------- | ------------------------------------------ |
| Personal voice / Telegram / daily digest           | `hermes/profiles/personal/CLAUDE.md`       |
| Mike-lawdbot Telegram, PR pipeline (Antfarm)       | `hermes/profiles/lawdbot/CLAUDE.md`        |
| Repo-wide refactor / multi-file coordination       | `hermes/profiles/codex/CLAUDE.md`          |
| Edge / SMS / sensor (Termux on Android)            | `hermes/profiles/mobile/CLAUDE.md`         |
| ConsultOps Marc routing, lead pipeline             | `hermes/profiles/consultops/CLAUDE.md`     |
| Sportsbook predictions, edge monitor               | `hermes/profiles/sportsbook/CLAUDE.md`     |
| Yehovah trial-to-GA ops monitoring                 | `hermes/profiles/yeh-ops/CLAUDE.md`        |
| Cross-squad strategy, weekly OKR roll-up           | `hermes/profiles/atlas-ceo/CLAUDE.md`      |
| Outbound (LinkedIn, email, prospect outreach)      | `hermes/profiles/viper-outreach/CLAUDE.md` |
| Content calendar, social posts                     | `hermes/profiles/quill-content/CLAUDE.md`  |
| Contract / compliance / SOC2 / audit               | `hermes/profiles/forge-audit/CLAUDE.md`    |
| Cost watching, ledger, fleet cie/apex briefing     | `hermes/profiles/ops/CLAUDE.md`            |
| AI research, framework audits, Sunday Weekly Brief | `hermes/profiles/vanclief/CLAUDE.md`       |

## Conventions

- **kebab-case** everywhere — file/dir names match Alex's filesystem protocol
- **Markdown-only context** — no proprietary formats anywhere in this tree
- **agentskills.io / SKILL.md** for every procedural skill — progressive disclosure (metadata → body → referenced files)
- **MCP for tools, A2A for agents** — never blur the line
- **One ADR per architectural decision** in `_meta/decisions/`, dated, never edit historical ADRs

## Source-of-truth ↔ runtime

`hermes/profiles/{name}/` (this repo, versioned in git) ↔ `~/.hermes/profiles/{name}/` (Hermes runtime).

- **Pull** runtime → versioned: `scripts/sync-profile.sh pull <name>` (nightly cron at 02:30 ET)
- **Push** versioned → runtime: `scripts/sync-profile.sh push <name>` (git `post-merge` hook)

Never hardcode `~/.hermes` paths in any profile — always use `HERMES_HOME` env var per the Hermes contributor guide.

## Dotfile registry — DO NOT MOVE

These tools live at env scope and stay where they are. Per-project addenda layer on top via project CLAUDE.md, never relocate the tools themselves.

- `~/.claude/` — Claude Code config, skills, agents, scripts, hooks
- `~/.openclaw/` — read-only archive after Phase 6 (90-day forensic window)
- `~/.codex/` — Codex CLI config + project_doc cache
- `~/.config/mission-control/` — legacy MC credentials (preserved through 90-day archive bridge)
- `~/.config/prettyfly-marketing/` — credentials
- `~/.mcp-auth/` — MCP server tokens
- `~/.ollama/` — local LLM runtime
- `~/.api-usage/` — token + cost tracking
- `~/.agents/skills/{rls-audit,staged-review}/` — env-scope skills (Codex review-agent — DO NOT migrate into this repo)
- `~/.local/bin/{hermes,closeout-stack}` — env-scope wrappers

## Kill-switch

`touch ~/.hermes/profiles/<name>/PAUSED` halts that profile's runtime. Same file at the tenant scope (`tenants/<slug>/PAUSED`) halts every profile for that tenant.

## Phase pointer

Phase tracker lives in `docs/migration-runbook.md`. Current phase: **0 complete** as of 2026-05-04.

## Codex parity

`AGENTS.md` is a symlink to this file. Edit only `CLAUDE.md`. Both Codex and Claude Code read the same context.
