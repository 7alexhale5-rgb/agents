---
date: 2026-05-18
type: decision
project: agents
tags: [adr, hermes, shared-skills, handoff]
status: accepted
parent_plan: ~/.claude/plans/here-is-what-we-joyful-torvalds.md
---

# ADR: Generate-Handoff Shared Skill

## Decision

Cross-session handoff generation is a shared Hermes skill, not profile-specific boilerplate.

The canonical skill lives at:

`hermes/shared-skills/generate-handoff/SKILL.md`

Profiles that do cross-session work should list `generate-handoff` in their routing docs and may invoke it manually at session close or phase transition.

## Shape

The skill writes handoffs with:

- YAML frontmatter
- state at handoff
- what remains
- validation steps
- critical references
- hard constraints
- pasteable resume prompt

## Boundary

The skill is manual-only for now. No automatic session-end hook is added until several handoffs prove the shape is stable.

## Why

Atlas and CMO both need clean context transfer. A shared skill makes that transfer reusable without growing each profile.
