---
date: 2026-05-18
type: decision
project: agents
tags: [adr, hermes, pfos, agent-events, cmo]
status: accepted
parent_plan: ~/.claude/plans/here-is-what-we-joyful-torvalds.md
---

# ADR: Hermes To PFOS Event Contract

## Decision

Hermes profiles may emit safe operational evidence to PFOS through the existing `agent_events` contract. PFOS is the command cockpit and evidence ledger; Hermes remains the profile/runtime side.

## Event Shape

Every Hermes event payload must be dashboard-safe:

```json
{
  "agent_slug": "cmo",
  "type": "cmo.weekly_decision.proposed",
  "status": "pending",
  "surface": "cli",
  "cwd_project": "marketing",
  "trace_id": "optional-run-id",
  "skill_slug": "weekly-review",
  "data": {
    "schema_version": "hermes.agent_event.v1",
    "title": "Weekly marketing decision proposed",
    "proposal_status": "proposed",
    "summary": "Safe operational summary only.",
    "runtime": "hermes",
    "private_payload_redacted": true
  }
}
```

Required fields: `agent_slug`, `type`, `status`, `surface`, `cwd_project`, and safe `data`.

Optional fields: `trace_id`, `skill_slug`, `confidence`, `source_refs`, and a related artifact path if it is repo-relative or vault-relative.

## Safety Rules

- No raw vault text.
- No secrets, prompts, memory dumps, or private Slack/email text.
- No absolute local filesystem paths in PFOS payloads.
- No claim that work executed unless a real execution receipt exists.
- Readout/proposal events are evidence, not execution.

## Canonical Event Types

| Event type | Status | Meaning |
| --- | --- | --- |
| `atlas.action.proposed` | `proposed` | Atlas created an approval proposal. |
| `atlas.action.approved` | `approved` | Alex approved an Atlas proposal. |
| `atlas.action.rejected` | `rejected` | Alex rejected an Atlas proposal. |
| `atlas.follow_up.queued` | `pending` | A safe follow-up brief was queued. |
| `atlas.follow_up.ready` | `completed` | Atlas recorded a safe follow-up brief. |
| `cmo.weekly_decision.proposed` | `pending` | CMO wrote a weekly readout proposal to the marketing inbox. |
| `cmo.eval.completed` | `completed` | CMO eval suite produced a safe summary. |
| `memory.health.reported` | `completed` | Memory/Obsidian health was summarized without raw note content. |

New profile events use `<profile>.<action>` or `<profile>.<object>.<action>` and must be documented in that profile's `CLAUDE.md`.

## CMO v1 Mapping

CMO's `weekly_decision.propose` writes a Markdown readout to `marketing/_inbox/cmo-readouts/` and emits one safe event:

- `agent_slug`: `cmo`
- `type`: `cmo.weekly_decision.proposed`
- `status`: `pending`
- `surface`: `cli` until PFOS adds a first-class `hermes` surface enum
- `cwd_project`: `marketing`
- `skill_slug`: `weekly-review`
- `data.private_payload_redacted`: `true`
- `data.runtime`: `hermes`
- `data.proposal_status`: `proposed`

The event data may include counts, decision, confidence, source file names, and the readout's vault-relative path. It may not include the full readout body.
