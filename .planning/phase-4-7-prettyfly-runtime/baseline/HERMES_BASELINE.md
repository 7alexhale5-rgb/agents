# Hermes baseline measurement — Phase 4.7 Gate G1

> **Status:** template — to be populated over 7 nights of nightly eval runs starting 2026-05-06. Output of `scripts/email-triage-eval-nightly.sh --capture-baseline`.

## Purpose

Establish what Hermes v0.12.0 actually scores on our 30-question golden set under our real workload, and what its actual cost-per-session profile is. Phase 4.7's 4.7.2 Ragas gate and 4.7.5 latency/cost gates are calibrated against these numbers; without baseline, gates are arbitrary.

## Required captures (one row per night, 7 nights minimum)

| Night | Date | Promptfoo Wilson lower-CI | Ragas faithfulness | Cost-per-session p50 | Cost-per-session p95 | Latency p95 | Trace volume / 24h |
| ----- | ---- | ------------------------- | ------------------ | -------------------- | -------------------- | ----------- | ------------------ |
| 1     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |
| 2     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |
| 3     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |
| 4     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |
| 5     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |
| 6     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |
| 7     | TBD  | TBD                       | TBD                | TBD                  | TBD                  | TBD         | TBD                |

## Per-profile breakdown (after 7 nights)

| Profile        | Wilson lower-CI | Ragas | Cost p50 | Cost p95 | Latency p95 |
| -------------- | --------------- | ----- | -------- | -------- | ----------- |
| personal       | TBD             | TBD   | TBD      | TBD      | TBD         |
| atlas-ceo      | TBD             | TBD   | TBD      | TBD      | TBD         |
| consultops     | TBD             | TBD   | TBD      | TBD      | TBD         |
| sportsbook     | TBD             | TBD   | TBD      | TBD      | TBD         |
| lawdbot        | TBD             | TBD   | TBD      | TBD      | TBD         |
| yeh-ops        | TBD             | TBD   | TBD      | TBD      | TBD         |
| forge-audit    | TBD             | TBD   | TBD      | TBD      | TBD         |
| viper-outreach | TBD             | TBD   | TBD      | TBD      | TBD         |
| quill-content  | TBD             | TBD   | TBD      | TBD      | TBD         |
| ops            | TBD             | TBD   | TBD      | TBD      | TBD         |
| codex          | TBD             | TBD   | TBD      | TBD      | TBD         |
| mobile         | TBD             | TBD   | TBD      | TBD      | TBD         |
| vanclief       | TBD             | TBD   | TBD      | TBD      | TBD         |

## Decision rule (after 7 nights)

| Hermes Ragas median | PF Runtime 4.7.2 gate becomes                                         |
| ------------------- | --------------------------------------------------------------------- |
| ≥ 0.85              | "match Hermes ±0.02"                                                  |
| 0.80–0.85           | "match Hermes ±0.02 AND clear 0.80 floor"                             |
| < 0.80              | **HALT** — issue is upstream of runtime choice, fix Hermes-side first |

## Notes

- Nightly run schedule already exists via launchd: `com.prettyfly.email-triage-eval-nightly` (per ADR-003).
- `--capture-baseline` flag (to add to `email-triage-eval-nightly.sh`) writes results to `.planning/phase-4-7-prettyfly-runtime/baseline/eval-night-{N}.log`.
- Aggregator script: `.planning/phase-4-7-prettyfly-runtime/baseline/aggregate.py` (TODO) reads the 7 logs and emits the tables above.
