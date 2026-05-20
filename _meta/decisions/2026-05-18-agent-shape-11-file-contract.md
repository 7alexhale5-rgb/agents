---
date: 2026-05-18
type: decision
project: agents
tags: [adr, hermes, profiles, agent-shape, cmo]
status: accepted
parent_plan: ~/.claude/plans/here-is-what-we-joyful-torvalds.md
---

# ADR: Agent Shape 11-File Contract

## Decision

Every active Hermes profile follows the Atlas-derived profile shape before it can be treated as a real agent.

Required files and directories:

| Path | Role |
| --- | --- |
| `SOUL.md` | Identity, voice, persona, and emotional posture. |
| `DOCTRINE.md` | Decision rules and canonical source references. |
| `USER.md` | Alex-specific context and preferences for this role. |
| `MEMORY.md` | Boot memory, durable anchors, and current operating context. |
| `CLAUDE.md` | Profile router: task routing, model routing, tools, boundaries, acceptance gate. |
| `AGENTS.md` | Symlink to `CLAUDE.md` for Codex parity. |
| `manifest.json` | Hermes SKU/runtime manifest. |
| `a2a-card.json` | A2A identity and authority card. |
| `config.yaml` | Runtime config: models, tools, channels, memory, approvals, guardrails. |
| `PAUSED.template` | Kill-switch placeholder. |
| `changelog.md` | Profile history and promotion evidence. |
| `skills/` | Flat single-file Markdown skills. |
| `eval/` | Evaluation docs, fixtures, and promptfoo or equivalent config. |

This is called the "11-file contract" because `skills/` and `eval/` are capability directories rather than identity files; `changelog.md` is required as profile history.

## Rules

- `AGENTS.md` is always a symlink to `CLAUDE.md`.
- Skills stay flat: only Markdown files directly inside `skills/`; no nested skill directories.
- A profile starts at rung 1 unless a written promotion gate says otherwise.
- Doctrine references canonical source docs rather than copying large source material that will drift.
- Shared behavior belongs in shared skills; profile docs stay focused on identity, routing, boundaries, and decisions.

## Enforcement

`scripts/lint-profile.sh` validates this contract. During the early roster build it soft-warns and exits `0`; once five or more active profiles exist, the script can be flipped to hard-fail.

## Why

Atlas proved the shape. CMO is the second agent and should make the pattern cheaper for every future profile, not create another one-off surface.
