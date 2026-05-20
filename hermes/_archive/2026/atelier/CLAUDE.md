# CLAUDE.md — `atelier` profile

> **Profile:** atelier · **Tier:** pro · **Channels:** cli
> **Phase:** 7 scaffold (2026-05-07) · skills authoring deferred to next wave

You're inside the atelier profile. Persona in `SOUL.md`, operator in `USER.md`,
cross-session decisions in `MEMORY.md`. This file routes per-task.

## Per-task routing (Layer 2)

| Task                                                   | Read                               | Skills           |
| ------------------------------------------------------ | ---------------------------------- | ---------------- |
| Generate DESIGN.md from brief / screenshot / brand kit | `skills/design-md-author/SKILL.md` | design-md-author |
| Execute /design-stack on a project task                | `skills/design-stack-run/SKILL.md` | design-stack-run |
| Ingest reference URL into design-library               | `skills/library-curate/SKILL.md`   | library-curate   |
| Audit project for DESIGN.md / system.md drift          | `skills/design-audit/SKILL.md`     | design-audit     |

Before any of the above, read in order: `<cwd>/DESIGN.md`, `<cwd>/.interface-design/system.md`,
`<cwd>/CLAUDE.md`. If `DESIGN.md` is missing, fall back to
`~/.claude/references/build-category-atlas.md` (per `~/Projects/CLAUDE.md`
§ Per-Project Design System precedence rule).

## Model routing

| Task class | Model               | Why                                                                      |
| ---------- | ------------------- | ------------------------------------------------------------------------ |
| Cheap      | `claude-haiku-4-5`  | Lint passes, token grep, library URL fetches, drift detection scans      |
| Drafting   | `claude-sonnet-4-6` | DESIGN.md drafts, component scaffolds, library entry summaries (default) |
| Reasoning  | `claude-opus-4-7`   | Token system design, cross-project refactors, complex audits             |
| Strategic  | `claude-opus-4-7`   | New design system from brief, multi-project token migrations             |

## MCP servers attached

- `pencil` (stdio) — `.pen` design-file editor; tools `batch_get`, `get_screenshot`,
  `find_empty_space_on_canvas`, `export_nodes`
- `playwright` (stdio) — JS-rendered reference capture for library curation
- `filesystem` (stdio, scoped to `~/Projects`) — read project DESIGN.md / system.md;
  `delete` excluded
- `design-library` (stdio, **deferred** to Phase 6) — see `config.yaml` for the
  commented-out block

## Hard rules

1. **No inline hex outside `DESIGN.md`.** Every color reference is a token name.
   This is a lint-checkable contract; violations block PRs.
2. **Cross-project mutations route through git PR on `atelier/<project>/<task>` branch.**
   The repo allowlist lives in `config.yaml` § `mutation_approval.repos`. Atelier
   refuses mutations to any path not on the allowlist. Signed commits required.
3. **Self-mutations route through `pf_runtime/dream/bounds_audit.py`.** This profile
   is non-personal; per `MEMORY_LIFECYCLE.md`, mutations to `MEMORY.md` and
   self-authored skills require operator approval (`skill_gen.autonomy: approve`).
4. **Outbound to humans = Alex tap required** (`approval.mode: explicit_for_outbound`).
5. **No money-flowing pipelines.** Read-only across ConsultOps Marc, sportsbook,
   mike-lawdbot, YEH ops.

## Acceptance gate

For any task to be considered complete, all three must hold:

1. `DESIGN.md` lints clean via `npx @google/design.md@<pinned> lint DESIGN.md`
2. The trace span emits all required `pf_runtime.*` attributes per `TRACE_SCHEMA.md`
3. The PFOS event surfaces in the fleet silo within 5 minutes of task completion
   (skill_slug, surface, cwd_project, parent_run_id all populated per the
   `agent_events:write` contract)

## Phase pointer

Plan: `~/.claude/plans/snug-crafting-fox.md`. Phase 7 scaffold complete 2026-05-07.
Phase 7.4 (skills SKILL.md authoring) gates Layer-1 routing entry in
`~/Projects/agents/CLAUDE.md`.

## Codex parity

`AGENTS.md` is a symlink to this file. Edit only `CLAUDE.md`.
