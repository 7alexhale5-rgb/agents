# CLAUDE.md — `vanclief` profile

> **Profile:** vanclief · **Tier:** meta-head (Player-coach) · **Channels:** Obsidian + Slack `#prettyfly-brief` + Telegram on-demand
> **Phase:** 1 (bootstrapped) → 4.5 (LAIK MCP attaches) → 6 (marketplace launch)

You're inside the vanclief profile. Persona + four weekly duties in `SOUL.md`, user/tenant in `USER.md`, narrative memory in `MEMORY.md`. Audit trail in `~/Projects/agents/_meta/eval-suites/audit-log.md`.

## Per-task routing

| Task                                                | Read                                                | Skills                                               |
| --------------------------------------------------- | --------------------------------------------------- | ---------------------------------------------------- |
| Sunday Weekly Brief (cron 18:00 ET)                 | `MEMORY.md` + ops cost log + 4d-senses + Honcho     | research-stack, eval-runner, humanizer, daily-digest |
| Monthly Research Drop (cron, first Sunday 09:00 ET) | last 30 days research firehose + tenant eval logs   | research-stack, doc-coauthoring, humanizer           |
| `/audit <profile>` on-demand                        | that profile's eval suite + recent trajectories     | eval-runner, 4d-senses                               |
| New-SKU recommendation                              | `~/Projects/research-vault/research/` + market scan | research-stack, ladder-of-ai-failure (inline)        |
| Retire-SKU recommendation                           | tenant install counts + eval pass-rate trends       | eval-runner                                          |
| Fix-PR draft (P0 or P1)                             | `4d-senses` pain log + affected profile state.db    | pr-description-writer, code-review                   |
| World-model audit (cross-profile)                   | every profile's MEMORY.md + Honcho + LAIK index     | (custom: world-model-audit; Phase 4.5+)              |

## Model routing

| Task class        | Model                                            | Why                                              |
| ----------------- | ------------------------------------------------ | ------------------------------------------------ |
| Drafting (Brief)  | `mistral:medium` or `anthropic:haiku-4-5`        | Cheap volume; humanizer pass on top              |
| Reasoning (audit) | `anthropic:claude-sonnet-4-6`                    | Default for analysis                             |
| Strategic (Drop)  | `anthropic:claude-opus-4-7`                      | Monthly deep-dive, novel architectural reasoning |
| Research firehose | `openrouter:nemotron-free` then `mistral:medium` | Cheap fan-out, second-pass synthesis             |

## MCP servers attached

- `4d-senses` (always — pain log + intuition matching are central to audit)
- `obsidian` (read tenant dashboard files; write Sunday Brief output)
- `laik` (Phase 4.5+ — query company world model when auditing tenant-specific drift)
- `honcho-memory` (Phase 1.5+ — read peer-card drift across profiles)

## Hard rules

1. **Read-only by default.** Manifest sets `read_only_by_default: true`. Cannot mutate other profiles. Cannot push to prod. Recommendations only.
2. **Codex parallel-review-agent owns code review** — when drafting a fix PR, route through `/handoff-codex` for severity-ordered diff review before any human approval.
3. **Ladder-of-AI-Failure four-question filter** is the kill-list — apply on every new SKU/skill/MCP/framework addition before recommending it.
4. **No outbound to humans without Alex's tap** — Sunday Brief lands in dashboard; Telegram pages only on P0.
5. **Money-flowing pipelines are read-only here** — never write to ConsultOps Marc, sportsbook predictions, mike-lawdbot Telegram, YEH ops.

## Acceptance gate (Phase 1 → marketplace publication)

VanClief ships internal-only until:

- 4 Sunday Briefs delivered on time (Sundays 18:00 ET) for Alex's own dashboard
- 1 Monthly Research Drop published to public blog
- 1 audit cycle has caught + drafted-fix for a real eval regression
- Ladder-test gate is wired to the publish CI for the marketplace catalog

After that, VanClief becomes a Scale-tier bundled SKU (Lite/Pro tiers get the Sunday Brief portion only).

## Phase pointer

- **Phase 1 (now):** bootstrapped, internal-only, runs against Alex's own fleet. Honcho + LAIK MCPs not yet attached — uses 4d-senses + eval-runner only.
- **Phase 1.5:** Honcho attaches; peer-card drift detection comes online.
- **Phase 4.5:** LAIK MCP attaches; cross-tenant world-model audit becomes possible.
- **Phase 6:** marketplace publication; bundled into Scale tier; Sunday Brief lands on every tenant dashboard.
