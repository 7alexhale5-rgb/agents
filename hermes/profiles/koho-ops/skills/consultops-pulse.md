---
name: consultops-pulse
description: Produce a source-grounded Rung 1 ConsultOps Pulse for the Koho-Ops profile.
input: optional report date and explicit source packet override
output: markdown ConsultOps Pulse shaped for future _inbox/koho-ops/ use
---

# Skill: consultops-pulse

## Purpose

Create a read-only ConsultOps Pulse for Koho retainer delivery. The Pulse answers what is true now, what proof exists, what still needs approval, what must not be enabled, and the next safest 1% Hermes move.

This is a Rung 1 profile-local skill. It reads approved source packets and current repo status only. It does not create runtime authority, send messages, mutate repositories, probe production, deploy, or write databases.

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

1. `Current Answer`
2. `Ready Proof`
3. `Approval Needed`
4. `Do Not Enable Yet`
5. `Repo And Source State`
6. `Next 1% Move`
7. `Source Basis`

Keep the Pulse concise. Every operational claim must trace to ConsultOps Pulse v0, current wiki context, current repo status, or a clearly named missing source. Separate ConsultOps from Excerpa; do not collapse both into generic Koho work.

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
- No `koho_ops.report.propose` or other propose-write contract in Rung 1.

`_inbox/koho-ops/` is the future local output surface only. This skill may describe the manual Pulse shape, but it does not grant write authority or runtime output authority by itself.

## Verification Checklist

Before considering a Pulse complete:

- Confirm `ConsultOps Pulse v0` is cited as a source packet.
- Confirm current repo state is labeled as observed, missing, or unavailable.
- Confirm `Do Not Enable Yet` explicitly blocks production probes, sends, runtime sync, deploys, database writes, and Koho repo mutations.
- Confirm the next move is one Hermes 1% move, not a broad ConsultOps delivery plan.
- Confirm no secrets, tokens, raw credentials, private messages, or client-facing sends appear in the output.
