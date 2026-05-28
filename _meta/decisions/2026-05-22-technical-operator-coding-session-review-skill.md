---
date: 2026-05-22
type: decision
project: agents
tags: [adr, hermes, profiles, technical-operator, coding-session-review, rung-1, yagni, sine]
status: accepted
related_adrs:
  - 2026-05-20-technical-operator-profile-scope.md
  - 2026-05-20-reserve-codex-for-tool-use-technical-operator-profile.md
  - 2026-05-18-agent-shape-11-file-contract.md
  - 2026-05-18-hermes-pfos-event-contract.md
---

# ADR: Add `coding-session-review` As A Rung-1 Technical-Operator Skill

## Decision

Add one profile-local skill, `coding-session-review`, to `technical-operator`.

This skill reviews a coding session as an operating artifact: the user request or handoff, current repo state, git diff, validation evidence, and any relevant inbox or operator artifact. It produces a read-only session receipt with verdict, risks, validation status, memory/handoff notes, and the next 1% developer move.

It does not create a new profile, tool, channel, cron, MCP server, deploy path, or external send surface. It writes only to `~/Projects/agents/_inbox/technical-operator-reviews/` and uses the existing `technical_operator.review.proposed` event surface.

## Why

Claude/Codex logs show a repeated coding-session loop:

`resume context -> plan architecture -> implement fast -> review/audit -> capture handoff -> choose next 1% move`

The highest-leverage agentic surface is not a generic coding agent. It is the continuity and review layer around coding sessions: make every session end with evidence, risk state, and the next small move.

This follows the Will-brain Hermes profile rule: start from repeated real work, keep the profile narrow, prove the workflow before adding orchestration, and promote only when memory or scheduling earns it.

## Authority Boundary

- Rung stays 1.
- No source edits.
- No commits, pushes, deploys, migrations, external sends, CI reruns, or production changes.
- No new built-in tool contract.
- No new event type.
- No write path outside `_inbox/technical-operator-reviews/`.
- No autonomous remediation loop.

## Acceptance

The slice is accepted when:

- `hermes/profiles/technical-operator/skills/coding-session-review.md` exists;
- `technical-operator` routing docs name the skill;
- `manifest.json` lists `coding-session-review`;
- `scripts/lint-profile.sh technical-operator` passes or has no new warnings caused by this slice.

## 1% Engineer Move

Run `coding-session-review` against the next completed coding session before adding any more technical-operator skills. If the receipt does not improve handoff quality, do not promote the workflow.
