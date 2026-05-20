---
adr: 007
title: Agentic OS hybrid runtime lanes
date: 2026-05-16
status: accepted
amends:
  - 2026-05-06-prettyfly-runtime-bare-metal.md
related:
  - 2026-05-05-substrate-architecture.md
  - 2026-05-05-litellm-routing-stack.md
  - 2026-05-16-jack-roberts-hermes-claude-code-agentic-os-extraction.md
operator_authorization: |
  Alex selected the hybrid cockpit path, runtime lanes as the first proof, and observe+recommend authority for v1.
---

> **Partially superseded by 2026-05-18 $1M pivot (commit `7e1340c`):** The cockpit-and-lanes framing stands — PFOS as command cockpit, multiple runtime lanes visible side-by-side. The `pf_runtime` lane is dead (PF Runtime archived to `_archive/2026/pf-runtime/`). The active lane registry is now `hermes_canonical`, `openclaw_external`, `claude_code`, `codex`, `manual_operator`. The "no unmeasured hybrid mode" guardrail and the safe-event-payload rules still bind. See `~/.claude/plans/here-is-what-we-joyful-torvalds.md` and `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`.

# ADR-007 — Agentic OS hybrid runtime lanes

## Context

ADR-006 made PF Runtime the canonical owned runtime and said there would be no hybrid mode after cutover. The next round of Jack Roberts / Hermes / Claude Code analysis changed the shape of the question. The useful pattern is not a permanent pile of duplicate runtimes. It is a cockpit that shows separate lanes with clear health, cost, events, authority, and retirement gates.

PFOS already has the correct spine: `agent_events`, `agent_actions`, source packets, traces, approvals, and dashboard surfaces. PF Runtime already owns the profile loop for first-party agents. Hermes, OpenClaw, Claude Code, and Codex remain useful only when they are visible as bounded lanes instead of being blurred into one assistant.

## Decision

Adopt a measured hybrid cockpit:

1. PFOS is the command cockpit and evidence ledger.
2. PF Runtime is the canonical runtime for owned Hermes-profile agents.
3. Hermes remains a frozen reference/profile source until explicit retirement.
4. OpenClaw, Claude Code, Codex, and manual operator work may remain visible as runtime lanes when they emit safe evidence.
5. Atlas is the CEO operating advisor, not the operating system.
6. Runtime lanes do not grant new authority. V1 is observe and recommend only.

This amends ADR-006's "no hybrid mode" line to: **no unmeasured hybrid mode**. A lane may remain only while it has a named purpose, safe telemetry, and a promotion or retirement gate.

## Runtime lanes

Initial display-level lanes:

| Lane                | Purpose                               | Authority                       |
| ------------------- | ------------------------------------- | ------------------------------- |
| `pf_runtime`        | Owned profile execution path          | Profile-specific, receipt-gated |
| `hermes_reference`  | Frozen reference and profile source   | Read/reference only             |
| `openclaw_external` | Mike/OpenClaw legacy service lane     | External observed service       |
| `claude_code`       | Repo implementation lane              | Operator-controlled             |
| `codex`             | Implementation, review, planning lane | Operator-controlled             |
| `manual_operator`   | Alex-approved human action lane       | Human only                      |

PFOS keeps the existing `agents.runtime` enum: `pf_runtime | external | legacy`. Runtime lanes are a display/source-packet derivation from agent rows and event surfaces, not a new database enum in v1.

## Guardrails

- No raw prompts, Slack/email text, secrets, memory dumps, or private source text in lane payloads.
- No new scheduler, queue, or executor primitive for this decision.
- No profile earns higher authority without evals, receipt gates, and visible PFOS evidence.
- Profile-vs-skill rule remains strict: persona-distinct voice, long-running state, and channel-isolated identity are required for a full profile.

## Consequences

**Wins**

- Jack-style runtime badges without collapsing the stack into a vague mega-agent.
- PFOS can compare health, costs, and event coverage across lanes.
- Cutover and retirement decisions become evidence-driven instead of ideological.

**Costs**

- ADR-006 retirement language needs careful reading from this point forward.
- Runtime-lane derivation must stay conservative until live event coverage improves.

## First proof

The first proof is a display-only runtime-lane registry in PFOS, backed by existing agent rows and recent `agent_events`. Atlas source packets may include lane summaries, but no lane gains new execution authority from this ADR.
