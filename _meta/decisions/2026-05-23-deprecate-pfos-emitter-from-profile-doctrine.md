---
date: 2026-05-23
type: decision
project: agents
tags:
  [
    adr,
    hermes,
    profiles,
    pfos,
    deprecation,
    doctrine,
    local-receipts,
    sine,
    yagni,
  ]
status: accepted
related_adrs:
  - 2026-05-22-hermes-webui-primary-workbench.md
  - 2026-05-18-hermes-pfos-event-contract.md
  - 2026-05-18-agent-shape-11-file-contract.md
  - 2026-05-22-technical-operator-coding-session-review-skill.md
---

# ADR: Deprecate PFOS Emitter From Profile Doctrine

## Decision

Every Hermes profile's doctrine now writes Hermes local receipts to `~/Projects/agents/_inbox/<profile>-{slug}/` instead of POSTing to the PFOS `agent_events` silo.

The emitter at `hermes/lib/agent_events.py` is unchanged and stays operational. It is the **legacy** path; profile skills do not call it unless Alex explicitly reopens PFOS for a workflow. The deprecation is doctrinal, not structural — no code in `hermes/lib/` was removed, no schema migration, no runtime change.

This ADR is the per-profile implementation of [`2026-05-22-hermes-webui-primary-workbench.md`](2026-05-22-hermes-webui-primary-workbench.md).

## Why

The webui ADR froze PFOS as the agent workbench surface and named Hermes WebUI primary. That decision left a question open: do profile skills still POST `agent_events` to PFOS as a side channel, or do they stop emitting altogether?

Two facts pushed the answer toward local receipts:

1. The reference implementation already shipped. The technical-operator `coding-session-review` skill (committed `47a219b`, ADR [`2026-05-22-technical-operator-coding-session-review-skill.md`](2026-05-22-technical-operator-coding-session-review-skill.md)) writes only to `_inbox/technical-operator-reviews/`. It produced four useful receipts before the skill itself was formally accepted. Local receipts are demonstrated, PFOS emission is the question.
2. The Karpathy ladder rung-1 contract calls for the simplest end-to-end first. Local markdown receipts in a directory the operator can grep are simpler than a Postgres event silo with bearer auth, contract enforcement, and a workbench UI that just got frozen.

## Rename patterns by profile

The migration touches `a2a-card.json` `channels`, `authority.can_read`, and `authority.can_write` strings, plus doctrine prose in `CLAUDE.md`, `DOCTRINE.md`, `config.yaml`, and every `skills/*.md`. Three patterns:

| Pattern           | Profiles                                      | a2a-card strings                                                                                                                                                                                                                                                                        |
| ----------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Local-receipts    | technical-operator, quill, stet, morning-logs | `pfos_evidence` → `hermes_local_receipts`; `pfos_agent_events_proposal_only` → `hermes_local_receipts_proposal_only`                                                                                                                                                                    |
| Receipts-flavored | atlas-ceo                                     | `pfos_evidence` → `hermes_receipts`; `pfos_source_packet` → `hermes_source_packet`; `pf_runtime_local_fallback` → `local_fallback_packet`; `pfos_agent_actions_proposed_only` → `hermes_agent_actions_proposed_only`; `pfos_follow_up_evidence_only` → `hermes_follow_up_evidence_only` |
| Minimal           | marin                                         | `safe_pfos_event_summary` → `safe_hermes_receipt_summary`                                                                                                                                                                                                                               |

Prose follows a uniform shape: "write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow."

## Authority boundary

- No edits to `hermes/lib/agent_events.py`. The emitter contract enforcement (`agent_slug`, `type`, `status`, `surface`, `cwd_project`, `skill_slug`, `runtime`, `private_payload_redacted`) stays intact for explicit reopens.
- No new code in `hermes/lib/` for a "local receipt writer." Receipts are hand-written markdown to `_inbox/` directories by each skill.
- No gateway changes, no `~/.hermes/` runtime changes, no plugin updates.
- No schema or migration; this is a source-tree doctrine change.

## Acceptance

The slice is accepted when:

- All six profile `a2a-card.json` files carry the new channel/can_read/can_write strings.
- All six profile `CLAUDE.md` / `DOCTRINE.md` / `config.yaml` / `skills/*.md` describe Hermes local receipts as the default and label `agent_events.py` as legacy.
- Repo-wide grep for `pfos_evidence`, `pfos_source_packet`, `pf_runtime_local_fallback`, `pfos_agent_actions_proposed_only`, `pfos_follow_up_evidence_only`, `pfos_agent_events_proposal_only`, `safe_pfos_event_summary` returns zero hits.
- `scripts/lint-profile.sh` PASSes all six profiles.
- `hermes/lib/agent_events.py` shows no diff in this slice.

## 1% Engineer Move

Run one profile end-to-end through its full skill loop (Atlas weekly-ceo-operating-loop is the highest-leverage candidate), verify the local receipt landed at `_inbox/atlas-ceo-{slug}/`, before considering any per-profile re-enable of the PFOS emit path. If the receipt is useful and `agent_events.py` calls stay dark, the migration is complete. If a workflow genuinely needs PFOS approval-history persistence, reopen PFOS for that workflow only and document the reopen in a follow-up ADR.

## Reversal

This ADR is reversible by reverting the slice commit. The emitter code path is untouched, so any profile can re-add `agent_events.py` calls to its skills with no infrastructure work — only doctrine to update.
