# CLAUDE.md - `codex` placeholder

> **Status:** disabled placeholder | **Tier:** none | **Channels:** none
> **Decision:** `_meta/decisions/2026-05-20-reserve-codex-for-tool-use-technical-operator-profile.md`

Codex is the OpenAI tool and operator-controlled runtime lane, not an active
Hermes profile. This directory remains only as a historical placeholder until a
later archive or rename cleanup removes it.

## Per-task routing

| Task | Read | Skills |
|------|------|--------|
| None | ADR above | None |

## Model routing

None. Do not run this as a Hermes profile.

## Hard rules

1. Do not attach shared skills, crons, channels, tools, or runtime authority.
2. Do not treat Codex as an autonomous engineering agent.
3. Route future engineering governance planning to `technical-operator` only
   after that profile earns identity under the profile-trigger ADR.

## Acceptance gate

No promotion path. Archive or replace by explicit ADR only.
