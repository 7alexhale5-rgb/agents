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

- Nightly run schedule for G1 specifically: `com.prettyfly.g1-baseline-capture` (loaded 2026-05-06 18:42 ET, fires daily at 02:30 ET, executes `scripts/g1-baseline-capture.sh personal`). The earlier note pointing G1 at `com.prettyfly.email-triage-eval-nightly` was incorrect — that plist runs the Promptfoo provider eval, a different artifact.
- `com.prettyfly.email-triage-eval-nightly` continues to run the email-triage Promptfoo SKU eval (per ADR-003) and is unchanged.
- Aggregator script: `.planning/phase-4-7-prettyfly-runtime/baseline/aggregate.py` (TODO) reads the 7 logs and emits the tables above.

## Capture environment (locked 2026-05-06 PM)

The pre-G1 5-agent swarm review surfaced four readiness gaps that landed before night-1 starts. Recording them here so the 7 captured rows are interpretable as a coherent baseline.

1. **Hermes config schema bug fixed.** Profile config.yaml previously used `model.default_model` / `model.default_provider` / `model.routing` — none of which Hermes v0.12.0 reads. Confirmed at `agent/auxiliary_client.py:1305-1342` the canonical keys are `model.default` and `model.provider`. Pre-fix, every agent loop fell through to the v0.12.0 hardcoded fallback chain (`google/gemini-3-flash-preview` for auxiliary, OR auto-router for main) and produced 0 successful round-trips. Patched in `hermes/profiles/personal/config.yaml`, `hermes/profiles/vanclief/config.yaml`, and the runtime mirror at `~/.hermes/profiles/personal-baseline/config.yaml`. Personal-baseline source-of-truth re-versioning is a follow-up (currently lives only in runtime).
2. **Default model now `nvidia/nemotron-3-nano-30b-a3b:free`.** The previous `nvidia/nemotron-nano-9b-v2` no longer in OR's free rotation; OR account is currently at zero credits (every paid slug returns HTTP 402). The `:free` variant is in the live OR catalog, returns `{"cost": 0}` per the live probe, and is the closest match to the original "drafting/digest tier" intent. Cost-per-session metric will read `$0` on every session for the duration of the OR-credits-empty state — node that against the Phase 4.7.5 cost-floor gate.
3. **G1 capture profile changed from `personal-baseline` to `personal`.** `personal-baseline` has no Slack inbound channel and would never accumulate sessions to baseline. `personal` is the only profile with a running Slack gateway (`@iris` in PrettyFly.ai workspace, launchd `ai.hermes.gateway-personal`). The original split-workspace design (per PLAN.md §5.1) is preserved for future PF Runtime A/B work in sub-phase 4.7.4.
4. **Slack `groups:read` scope still missing on the Iris bot.** Causes a recurring `channel_directory: failed to list Slack channels` warning every 5 min. Non-blocking for G1 (DMs work; only private-channel discovery is affected). Operator action when convenient: add `groups:read` to the Iris Slack app at api.slack.com/apps, reinstall.
   2026-05-06 personal SKIP sessions=1 min=5 hermes=Hermes Agent v0.12.0 (2026.4.30)
   Project: /Users/alexhale/.hermes/hermes-agent
   Python: 3.11.14
   OpenAI SDK: 2.32.0
   Update available: 278 commits behind — run 'hermes update'@0ce1b9fe2 schema=1
   2026-05-06 personal SKIP sessions=1 min=5 hermes=Hermes*Agent_v0.12.0*(2026.4.30)@0ce1b9fe2 schema=1
   2026-05-06 personal-baseline SKIP sessions=1 min=5 hermes=Hermes*Agent_v0.12.0*(2026.4.30)@0ce1b9fe2 schema=1
   2026-05-06 personal SKIP sessions=2 min=5 hermes=Hermes*Agent_v0.12.0*(2026.4.30)@0ce1b9fe2 schema=1
