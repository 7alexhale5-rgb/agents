# Phase 4.7 status tracker

> **Last updated:** 2026-05-06 (post fix-then-ship). Operator G0=YES locked. Pre-work artifacts shipped + 16-fix manifest applied + Codex re-review 0 critical / 2 high / 1 low (highs + low fixed in-pass). Phase 4.7.0 gate **CLEARED** (criterion: ≤2 critical findings = 0 actual).

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
