---
date: 2026-05-29
type: decision
project: agents
tags: [adr, amendment, hermes, slack, gateway, research-scout, rung-2, earn-path]
status: accepted
amends: 2026-05-24-hermes-active-slack-gateway-policy.md
related_adrs:
  - 2026-05-24-hermes-active-slack-gateway-policy.md
  - 2026-05-29-research-scout-fleet.md
plan: ~/.claude/plans/2026-05-29-phase-3-scout-fleet-surfaces.md
---

# ADR Amendment: Research Scout Fleet — Slack Earn-Path

## Purpose

This is an **amendment** to `2026-05-24-hermes-active-slack-gateway-policy.md`, not a
new grant. It defines **how a Research Scout Fleet scout earns a Slack gateway** —
the gate, the allowed surface, the boundary, the rollback, and the verification a
later activation decision must cite.

**This amendment activates no gateway.** The gateway policy's allowed live-state
table is unchanged: only `personal` and `atlas-ceo` run active Slack. No scout is
Slack-connected today, and none becomes so by virtue of this document.

## Why now

Phase 3 of the Research Scout Fleet surfaces digests to the morning brief and the
PFOS cockpit Intelligence lane (both read-only, both shipped). Slack 2-way is the
*next* surface, but the fleet doctrine (ADR `2026-05-29-research-scout-fleet.md`)
and the gateway policy both gate it behind rung 2. The four scouts cleared their
rung-1 acceptance gates on 2026-05-29 via v1 bootstrap digests — but rung-1 holding
across **one** run is not the rung-2 trigger. This amendment writes the earn-path
down now so the criteria are fixed before any scout reaches them, rather than
invented at activation time.

## The earn gate (per scout)

A scout becomes **eligible** to request a Slack gateway only when ALL hold:

1. Its rung-1 acceptance gate has held across **≥2 consecutive weekly digests** that
   Alex has **confirmed useful** (not merely landed). Confirmation is recorded in the
   scout's `changelog.md` with the digest dates.
2. Those digests are source-grounded and carry real CI-rubric verdicts — i.e. the
   scout is producing signal, not noise (SKIP-heavy weeks count as useful signal if
   the SKIP reasoning is sound).
3. The scout's versioned `config.yaml`, runtime state, and doctrine all still agree
   on its read-only + propose-only boundary (the rung-1 contract is intact).

Eligibility is necessary but **not sufficient**: activation still requires a separate
dated decision (below).

## Allowed Slack surface (when activated)

A scout that earns activation is constrained to the **Atlas boundary or tighter**:

- **Alex DM only.** No public-channel posting, no slash commands, no file sends, no
  third-party outbound, no autonomous execution.
- **Digest delivery only.** The scout may push its weekly digest headline + top
  verdict + a link/path to Alex's DM. It may **not** act on a finding over Slack — it
  remains a rung-1-style proposer; Slack is a delivery channel, not new authority.
- **No inbound command authority.** A scout does not accept "do X" instructions over
  Slack at activation. Inbound 2-way (Alex replies steer the next sweep) is a
  *further* rung that earns its own decision; first activation is outbound-digest only.

## Activation procedure (per scout, separate decision)

When a scout is eligible and Alex wants it on Slack:

1. Write a new dated ADR (or amendment) that **names the scout**, cites the ≥2
   confirmed-useful digest dates from its `changelog.md`, states the exact Slack
   surface (DM-only digest), and includes **live smoke evidence** (one test digest
   delivered to the DM, redacted token fingerprint only).
2. Update the gateway policy's allowed live-state table to add the scout.
3. Verify token ownership with local redacted fingerprints only — never commit,
   paste, or screenshot a raw Slack token (gateway-policy Operating Rule 2).

Until that decision exists for a given scout, the scout has no Slack access.

## Rollback

If an activated scout's gateway behaves outside its boundary:

1. Stop that scout's launchd Slack gateway.
2. Remove or rotate the affected Slack token from the scout runtime env.
3. Record the incident in the scout's `changelog.md`.
4. Require fresh smoke evidence before reconnecting.

Reversing this *amendment* (the earn-path policy itself) is a dated supersession
note; since it grants nothing, there is no gateway to disconnect.

## Verification (of this amendment)

- The gateway-policy allowed live-state table is unchanged (still `personal` +
  `atlas-ceo` only). Confirmed 2026-05-29.
- No scout `config.yaml` has `channels.slack.enabled: true` (all four remain
  `false`). This amendment changes no scout config.
- This file names: the gate, the surface, the boundary, the activation procedure,
  the rollback — satisfying gateway-policy Operating Rule 5's requirement for what a
  Slack-expanding ADR/amendment must contain, while deferring the actual expansion to
  a per-scout activation decision.
