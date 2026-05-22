---
name: daily-brief
description: Produce a read-only Hermes Morning Logs operational briefing.
input: optional report date
output: markdown to ~/Projects/agents/_inbox/morning-logs/{YYYY-MM-DD}-morning-logs.md
---

# Skill: daily-brief

## Purpose

Answer the daily operator questions:

- Is Hermes usable right now?
- What is broken?
- Which profile/event/approval needs Alex next?
- Where should Alex look in the dashboard first?

## Procedure

Run the collector:

```bash
python3 ~/Projects/agents/scripts/morning-logs.py
```

The collector reads Hermes dashboard APIs, Fleet, Labyrinth, protected Logs via the dashboard session token, and local git status. It writes one local report and emits one safe PFOS evidence event using the profile's `morning_logs.report.propose` event contract.

## Hard limits

- Do not restart the gateway.
- Do not kill any process.
- Do not edit config or keys.
- Do not execute approvals.
- Do not deploy, purchase, send, or mutate profiles.
- Do not put raw logs, secrets, prompts, or private messages into PFOS events.

## Output shape

The report must include:

- Hermes usable right now
- gateway state
- broken signals
- pending approvals count and oldest approval summary
- Labyrinth guidepost summary
- repo status summary
- recommended next action
- dashboard training loop
