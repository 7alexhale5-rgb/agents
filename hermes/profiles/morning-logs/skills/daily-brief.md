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
- Is memory trustworthy today?
- Are API spend, balances, and provider health safe enough for today's work?
- What is broken?
- Which profile/event/approval needs Alex next?
- Where should Alex look in the dashboard first?

## Procedure

Run the collector:

```bash
python3 ~/Projects/agents/scripts/morning-logs.py
```

The collector reads Hermes dashboard APIs, Fleet, Knowledge Vault, Labyrinth, `~/.api-usage/latest.json`, protected Logs via the dashboard session token, and local git status. It writes one local report and writes one safe Hermes-local evidence receipt using the profile's `morning_logs.report.propose` contract.

## Hard limits

- Do not restart the gateway.
- Do not kill any process.
- Do not edit config or keys.
- Do not expose raw provider billing payloads or API keys.
- Do not execute approvals.
- Do not deploy, purchase, send, or mutate profiles.
- Do not put raw logs, secrets, prompts, or private messages into receipts.

## Output shape

The report must include:

- Hermes usable right now
- gateway state
- memory trustworthiness
- broken signals
- pending approvals count and oldest approval summary
- Knowledge Vault freshness, retrieval, and memory-health summary
- API usage today/MTD totals, warning count, manual-review debt, degraded provider names, and operator dashboard path
- Labyrinth guidepost summary
- repo status summary
- recommended next action
- dashboard training loop
