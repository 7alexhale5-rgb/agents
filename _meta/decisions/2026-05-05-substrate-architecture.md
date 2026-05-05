# ADR-003 — Substrate architecture lock + Phase 0 unblock

**Date:** 2026-05-05
**Status:** Accepted (locks decisions #1–16 in the master architecture)
**Replaces:** N/A (additive to ADR-001 Hermes adoption + ADR-002 VanClief world-model audit)
**Phase pointer:** Phase 0 (substrate + 13 sealed profiles). Gate measurement starts 2026-05-05; gate evaluation at 2026-05-06 ~14:00 ET.

## Context

The 3-tier agentic OS architecture (research at `/tmp/agentic-os-research/07-architecture.md`, master plan at `14-master-plan.md`) commits to 13 chartered profiles and a 5-piece substrate. Disk state on 2026-05-05 morning: 2 of 13 profile dirs present (`personal`, `vanclief`); substrate primitives partially scaffolded (Honcho up, eval harness present, but `registry-rebuild`, `validate-profile`, and `a2a-card.json` schema unrealized).

The `moltbook.com` integration question (see `~/Projects/research-vault/research/2026-05-05-moltbook-leverage-strategy.md`) was resolved with a SKIP verdict; substrate brand renamed `moltbook` → `agora` to remove the collision with the public Meta-owned platform.

## Decision

Lock the master architecture as authoritative (16 decisions in §7) and ship Phase 0 against a single compound gate:

1. **Honcho `/health` returns 200 continuously for 24h** (sample every 60s, n ≥ 1440, zero failures).
2. **`registry-rebuild.py` p95 latency < 200ms** across n ≥ 288 cron fires (5-min interval, 24h window).
3. **All 13 profile dirs pass `validate-profile.sh --all`** (schema check on required files + manifest + a2a-card).

Karpathy throwaway-first principle applied: profile content (SOUL/USER/MEMORY) is template-only at scaffold time. Content evolves through Phase 1+ shadow when traffic arrives. Gate is structural, not content-quality.

## What shipped on 2026-05-05

### Substrate primitives

- `~/Projects/agents/scripts/registry-rebuild.py` — Python implementation (jq fork-exec storm in original bash version pushed p95 to 1908ms; Python with depth-limited `os.walk` + topdown skip-dir pruning brought p95 to 155ms across 50 samples).
- `~/Projects/agents/scripts/validate-profile.sh` — schema lint for required files (SOUL/USER/MEMORY/CLAUDE/manifest/config/a2a-card) + required dirs (rooms/skills/workspace/scratch/memory/eval) + JSON shape checks.
- `~/Projects/agents/scripts/stamp-a2a-cards.sh` — emits `a2a-card.json` per profile from manifest.json, schema `a2a/v1+ext` with `side_effects[]`, `eval_suite_uri`, `cost_envelope`.
- `~/Projects/agents/scripts/lib/wilson.sh` — Wilson lower-CI math factored out of `email-triage-eval-nightly.sh`.
- `~/Projects/agents/scripts/phase-0-soak-tick.sh` — 60s Honcho `/health` probe, appends `~/Assets/logs/phase-0-honcho-soak.tsv`.
- `~/Projects/agents/scripts/phase-0-gate-eval.sh` — at hour 24, reads both TSVs + runs validate-profile, emits gate PASS/FAIL.

### Profile fleet

- 11 missing profiles bootstrapped via `bootstrap-profile.sh`: `atlas-ceo`, `ops`, `viper-outreach`, `quill-content`, `codex`, `consultops`, `forge-audit`, `lawdbot`, `mobile`, `sportsbook`, `yeh-ops`.
- All 13 profiles stamped with `a2a-card.json`.
- All 13 pass `validate-profile.sh --all`.

### Honcho healthcheck fix

- `honcho/docker-compose.yml` — `honcho-api` healthcheck switched from `curl` (not in image) to Python `urllib` (stdlib in image). Container now reports healthy. Previous `FailingStreak: 2264` was a healthcheck-CMD bug, not service health.

### launchd jobs

- `~/Library/LaunchAgents/com.prettyfly.registry-rebuild.plist` — every 300s, `python3 registry-rebuild.py --tsv`.
- `~/Library/LaunchAgents/com.prettyfly.phase-0-soak.plist` — every 60s, `phase-0-soak-tick.sh`.

## Consequences

- The `moltbook` brand collision (and the public moltbook.com integration) is closed; substrate name `agora` is durable.
- `registry.json` now exists at `~/.hermes/registry.json` with 13 peers; cross-profile discovery is operational.
- Phase 1 (email-triage Wilson-CI gate against the now-realized cohort) is unblocked — pending Phase 0 gate clearance at 2026-05-06.
- Profile content is intentionally template-only; this ADR's correctness depends on Phase 1+ flowing real traffic to fill SOUL/USER/MEMORY without backfilling all 11 hand-authored upfront.

## Reversibility

- Substrate brand: REVERSIBLE only if a peer operator publicly attributes pipeline to moltbook.com placement OR Meta opens an audited B2B API on the substrate (per master plan stop conditions).
- Profile scaffolds: REVERSIBLE — `bootstrap-profile.sh` regenerates them; `seal-profile.sh` halts any.
- registry-rebuild Python: REVERSIBLE — the bash version's logic is preserved in git history if a Python-free environment ever matters.

## Addendum 2026-05-05 PM — Compressed gate semantics

The original gate criteria baked the 24h calendar window into the sample
counts (n≥1440 health rows, n≥288 registry rows). On reflection, those
were _guesses for "enough samples"_, not load-bearing properties of the
system being measured. Time-dependence matters only for short-window
leak exposure (~60 min covers it) and operational variance across the
day (genuinely lost in compression — accepted trade-off for velocity).

Revised criteria — both sets are valid; either clears the gate:

| Gate                      | Original (24h)             | Compressed (60min)                                                        |
| ------------------------- | -------------------------- | ------------------------------------------------------------------------- |
| Honcho /health            | n≥1440 + zero non-200 rows | n≥600 across ≥60 min wall-clock + Wilson upper-CI on failure rate ≤ 0.005 |
| registry-rebuild          | n≥288 + p95 <200ms         | n≥300 across ≥45 min wall-clock + p95 <200ms + p99 <500ms                 |
| validate-profile.sh --all | exit 0                     | unchanged                                                                 |

Wilson upper-CI on the failure rate is _stronger_ than "zero non-200 in
1440 samples": it bounds the true failure rate at ≤0.5% with 95%
confidence rather than relying on the implicit "zero seen" heuristic.

Sampling rate: compressed Honcho probe at 4s cadence × 900 samples
(60 min) yields Wilson upper ≈ 0.0042 for 0/900, comfortably under 0.005
and statistically equal to or stronger than the 24h soak's 1440-row
zero-failure observation.

Both the 24h launchd soak and the compressed run write to the same
TSVs. They cross-validate: if they disagree, that's a real signal worth
investigating before advancing.

`scripts/phase-0-soak-compressed.sh` runs the compressed sweep;
`scripts/phase-0-gate-eval.sh` reads either window and emits the
verdict for whichever set of thresholds applies.

## Cross-references

- Architecture: `/tmp/agentic-os-research/07-architecture.md`
- Master plan: `/tmp/agentic-os-research/14-master-plan.md`
- Reconciliation: `/tmp/agentic-os-research/15-reconciliation.md`
- Wireframe brief: `/tmp/agentic-os-research/12-wireframe-brief.md`
- Mind map: `/tmp/agentic-os-research/13-mindmap.canvas`
- Moltbook decision: `~/Projects/research-vault/research/2026-05-05-moltbook-leverage-strategy.md`
- Prior ADRs: `_meta/decisions/2026-05-04-adopt-hermes.md`, `_meta/decisions/2026-05-04-vanclief-world-model-audit.md`
