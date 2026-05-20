# CLAUDE.md — `~/Projects/agents/`

> **Status:** active | **Type:** tooling | **Phase:** $1M-pivot active (2026-05-18)
> **Mission:** Internal agent fleet driving PrettyFly CTO Advisory revenue to $1M ARR in 24 months. No marketplace.
> **Plan:** `~/.claude/plans/here-is-what-we-joyful-torvalds.md`
> **Strategy source:** `~/Projects/marketing/` (marketing vault)
> **Runtime:** Hermes Agent v0.12.0 (Nous Research, MIT). PF Runtime archived. See `~/Projects/memory-vault/decisions/2026-05-18-archive-pf-runtime.md`.

You've opened the consolidated Hermes monorepo. This file is the Layer-1 router (per JEVanClief's folder-as-workspace pattern). Use it to decide which profile to descend into.

## Active roster — 7 profiles

| Task                                                                                                | Descend to                                     |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Source-grounded CEO operating advisor; weekly brief; decision memos                                 | `hermes/profiles/atlas-ceo/CLAUDE.md`          |
| Weekly campaign decision + ICP + content direction + revenue-loop review                            | `hermes/profiles/marin/CLAUDE.md` (Phase 2)      |
| Content drafting from approved positioning (drafts to `_inbox/quill-drafts/`, never publishes)      | `hermes/profiles/quill/CLAUDE.md`              |
| Pre-launch pressure-test on campaigns, claims, positioning (critiques to `_inbox/stet-critiques/`) | `hermes/profiles/stet/CLAUDE.md`              |
| Koho retainer delivery (Marc routing, ConsultOps demos, Excerpa work)                               | `hermes/profiles/koho-ops/CLAUDE.md` (Phase 5) |
| Yehovah retainer delivery (trial-to-GA monitoring, CTO duties)                                      | `hermes/profiles/yeh-ops/CLAUDE.md` (Phase 5)  |
| Repo-wide refactor / multi-file coordination / PR drafts on revenue products                        | `hermes/profiles/codex/CLAUDE.md` (Phase 5.5)  |

Profiles in parentheses are scheduled for build per the plan; `atlas-ceo`, `codex`, `marin`, `quill`, and `stet` exist on disk as of 2026-05-20 (Phase 3 of $1M plan landed).

### Karpathy ladder per profile

- **Rung 1**: read-only source-grounded briefs
- **Rung 2**: propose-only writes (drafts to `_inbox/`, decisions to ledger, never executes)
- **Rung 3**: scoped tool actions with human approval gate
- **Rung 4**: routine actions (only after per-skill eval gates pass)

Atlas is at rung 3 — use it as the reference shape. Every new profile starts at rung 1 and earns each rung via gate.

### Archived (do not descend) — see `hermes/_archive/2026/`

`atelier` (kept as OSS, not as profile), `consultops` (old), `forge-audit`, `lawdbot` (mike-lawdbot fully sunsetting), `mobile`, `ops`, `personal`, `personal-baseline`, `quill-content` (old), `sportsbook`, `vanclief`, `stet-outreach` (old), `yeh-ops` (old; rebuild in Phase 5).

## Conventions

- **kebab-case** everywhere — file/dir names match Alex's filesystem protocol
- **Markdown-only context** — no proprietary formats anywhere in this tree
- **agentskills.io / SKILL.md** for every procedural skill — progressive disclosure (metadata → body → referenced files)
- **MCP for tools, A2A for agents** — never blur the line
- **One ADR per architectural decision** in `_meta/decisions/`, dated, never edit historical ADRs
- **1% closeout discipline** — after each completed task, name the next obvious 1% move. When Alex asks for planning around it, produce a decision-complete plan, then autonomously execute up to the next three small, safe 1% moves unless a real blocker appears.

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

**Current phase: $1M-pivot Phase 2 (Marin weekly decision pilot) — in progress 2026-05-18.**

Per `~/.claude/plans/here-is-what-we-joyful-torvalds.md`:

- Phase 1: archive dead weight (pf-runtime, marketplace, non-revenue profiles, experimental forks) ✅ landed 2026-05-18
- Phase 1.5: PrettyFly sub-project revenue audit (audit-engine, decision-maker-identifier, LAIK, gravity-stack-koho-starter, etc.)
- Phase 2: build Marin profile from Atlas template (1 week)
- Phase 3: build Quill + Stet from Atlas template (1 week)
- Phase 4: extend Atlas with marketing-vault read path (2-3 hours)
- Phase 5: build koho-ops + yeh-ops retainer-delivery profiles (2 weeks)
- Phase 5.5: rebuild codex profile from Atlas template (3-5 hours)
- Phase 6: wake one dormant Hermes capability (trigger-gated)
- Phase 7: quarterly compound review (every 90 days starting 2026-08-18)

Legacy migration tracker at `docs/migration-runbook.md` is historical record only — superseded by the $1M-pivot plan above.

## Codex parity

`AGENTS.md` is a symlink to this file. Edit only `CLAUDE.md`. Both Codex and Claude Code read the same context.
