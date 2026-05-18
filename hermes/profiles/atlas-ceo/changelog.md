# Changelog — atlas-ceo profile

## 2026-05-18 — first weekly brief adoption proof

- Restored PFOS cost visibility in production source packets: the Atlas packet
  now returns `business_scorecard.costs.available=true` through the
  `agent_events` rollup and no longer reports `sqlite3 CLI not found`.
- Produced a no-mutation PFOS approval queue triage artifact for the 20
  packet-visible pending actions: 0 approve, 9 reject, 11 expire.
- Cleared those 20 stale packet-visible actions in production as rejected
  stale-context decisions, with 20 paired redacted events and no execution.
- Cleared a second packet-visible stale backlog batch in production: 0 approve,
  20 reject, 20 paired redacted events, and no provider execution. The next
  packet still shows May 13 residue, so Atlas should plan durable stale
  resolution before another manual sweep.
- Ran the first live PFOS-backed Atlas weekly brief after the cost fix; the run
  returned `finish_reason=stop` with no degraded marker, no receipt
  hallucination, and no execution claim.
- Adopted the operating decision
  `clear_pending_approval_queue_before_new_surface_area`.
- Recorded a redacted PFOS evidence event
  `atlas.weekly_brief.adopted` as
  `6f7464af-4ac1-4cb1-92c4-de85b30c0776`.
- Kept Atlas at manual weekly CEO brief pilot until the pending queue-triage
  follow-through is completed.

## 2026-05-18 — manual weekly CEO brief pilot

- Restored the premium Atlas source-grounded route after provider credits were
  replenished.
- Ran a real PFOS-backed weekly CEO brief through
  `anthropic:claude-sonnet-4-6`; the output had no degraded marker and did not
  claim any proposal receipt or execution.
- Promoted Atlas from weekly CEO brief candidate to manual weekly CEO brief
  pilot. Scheduled cadence remains gated on live-brief adoption evidence and
  restored cost visibility.

## 2026-05-18 — weekly CEO brief candidate

- Passed the Atlas blind interview suite: 9/9 cases, zero fabricated metrics,
  zero false action claims, and zero role-collapse failures.
- Verified the production PFOS approval/follow-up loop: rich Slack feedback and
  minimal Slack approval both returned 200, `atlas.follow_up.ready` recorded,
  and `agent_actions.executed_at` stayed null.
- Promoted Atlas from incubating to weekly CEO brief candidate.
- Kept production real-brief promotion blocked on premium model-route credits:
  the eval run passed through fallback after Anthropic/OpenRouter reported
  insufficient credits.

## 2026-05-15 — CEO brief hiring bridge

- Added `fleet.snapshot` as Atlas's read-only source packet path.
- Moved Atlas toward source-grounded CEO briefs with local skills for packet
  triage, weekly briefs, and decision memos.
- Tightened Atlas's acceptance gate around no-source behavior, cited source
  signals, one-way/two-way door decisions, and zero fabricated metrics.
- Added a repeatable hiring rubric and fixture source packet under `eval/`.

## 2026-05-15 — CEO operating advisor graduation

- Added PFOS-first source packet expectations and business scorecard context.
- Added proposed-only Atlas action authority through `atlas.propose_action`.
- Archived legacy MC coordinator notes so they cannot override Atlas's CEO
  advisor boundary.
- Expanded Atlas profile-local skills and promptfoo eval coverage for source
  packets, scorecards, proposal drafting, and role-collapse guardrails.

## 2026-05-15 — Slack DM bring-up

- Wired Atlas as Alex-first/internal with Slack DM as the first communication path.
- Fixed `config.yaml` to use PF Runtime/Hermes model keys: `model.default` and
  `model.provider`.
- Added Slack token/home target keys to `.env.example`.
- Pushed profile source to `~/.hermes/profiles/atlas-ceo`.
- Verified PF Runtime can load `atlas-ceo`, produce a CLI reply, authenticate Slack,
  and post a live smoke message to Alex through the Atlas Slack adapter.

## 2026-05-05 — initial scaffold

- Created via `scripts/bootstrap-profile.sh atlas-ceo`
