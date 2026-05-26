---
name: consultops-pulse
description: Produce a source-grounded Rung 1 ConsultOps awareness pulse for the Koho-Ops profile.
input: optional report date and explicit source packet override
output: markdown ConsultOps awareness note for manual _inbox/koho-ops/ use
---

# Skill: consultops-pulse

## Purpose

Create a read-only ConsultOps awareness pulse for the Koho-Ops ear-to-the-ground profile. The Pulse answers where the project stands, what source updates exist, what context is stale or missing, and what the next safe check should be.

This is a Rung 1 profile-local skill. It reads approved source packets and current repo status only. It does not operate ConsultOps, Koho, Excerpa, or any client workflow. It does not create runtime authority, send messages, mutate repositories, probe production, deploy, or write databases.

## Required Reads

Read these before making any source-grounded claim:

- `hermes/profiles/koho-ops/CLAUDE.md`
- `hermes/profiles/koho-ops/DOCTRINE.md`
- `hermes/profiles/koho-ops/MEMORY.md`
- `/Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md`
- Koho wiki context from `/Users/alexhale/Projects/memory-vault/wiki/koho.md`
- ConsultOps wiki context from `/Users/alexhale/Projects/memory-vault/wiki/consultops.md`
- Current read-only ConsultOps repo status and recent log, normally:
  - `git status -sb`
  - `git log --oneline -8`
- Current read-only `process-automation` status, normally:
  - `git status -sb`

If a required source path or repo is unavailable, state that as missing source evidence. Do not fill gaps from memory.

## Output Shape

Use these headings in this order:

1. `Current State`
2. `Source Updates`
3. `Repo And Source State`
4. `Stale Or Missing Context`
5. `Boundaries`
6. `Next Check`
7. `Source Basis`

Keep the Pulse concise. Every status claim must trace to ConsultOps Pulse v0, current wiki context, current repo status, or a clearly named missing source. Separate ConsultOps from Excerpa; do not collapse both into generic Koho work. Do not turn source awareness into workflow instructions.

## Hard Boundaries

- No production probes.
- No sends or external-send preparation.
- No Slack, email, LinkedIn, calendar, SendPilot, SmartLead, or Waalaxy actions.
- No runtime sync.
- No deploys.
- No database writes.
- No workbook routing or workbook writeback.
- No proposal job starts.
- No Koho repo mutations.
- No workflow instructions.
- No action-authority promotion.

`_inbox/koho-ops/` is a manual local receipt surface only. This skill does not grant write authority or runtime output authority.

## Verification Checklist

Before considering a Pulse complete:

- Confirm `ConsultOps Pulse v0` is cited as historical source context, not an action plan.
- Confirm current repo state is labeled as observed, missing, or unavailable.
- Confirm `Boundaries` explicitly blocks production probes, sends, runtime sync, deploys, database writes, and Koho repo mutations.
- Confirm the next move is a check or source-freshness improvement, not a ConsultOps workflow plan.
- Confirm no secrets, tokens, raw credentials, private messages, or client-facing sends appear in the output.
