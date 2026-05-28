---
name: source-freshness-checklist
description: List the read-only sources to check for Koho-Ops project awareness.
input: optional lane name or date
output: markdown checklist for source freshness and repo state
---

# Skill: source-freshness-checklist

## Purpose

Keep Koho-Ops aligned as an ear-to-the-ground profile. This checklist answers only:

- What sources changed?
- What repo state changed?
- What context is stale or missing?
- What should we read next to stay oriented?

This skill is read-only. It does not operate ConsultOps, Koho, Excerpa, or any client work. It does not produce strategy, workflow instructions, external messages, or authority changes.

## Required Reads

Read these before producing the checklist:

- `hermes/profiles/koho-ops/CLAUDE.md`
- `hermes/profiles/koho-ops/DOCTRINE.md`
- `hermes/profiles/koho-ops/MEMORY.md`
- Relevant wiki pages from `/Users/alexhale/Projects/memory-vault/wiki/`
- Latest approved receipts from `/Users/alexhale/Projects/memory-vault/operator-artifacts/` for the requested lane
- Read-only repo state for relevant local repos:
  - `git status -sb`
  - `git log --oneline -8`
- Memory wiki health when source trust is part of the question:
  - `python3 /Users/alexhale/Projects/memory-vault/scripts/memory_hub.py --validate --strict-wiki`
  - `python3 /Users/alexhale/Projects/memory-vault/scripts/memory_hub.py --maintenance-queue --dry-run`

If a source is unavailable, mark it as missing. Do not infer missing state from memory.

## Output Shape

Use these headings in this order:

1. `Sources To Check`
2. `Observed Freshness`
3. `Repo State Checks`
4. `Stale Or Missing Context`
5. `Read Next`
6. `Boundaries`

## Rules

- Report status only.
- Prefer current repo state and newer receipts over older wiki summaries.
- Label each source as current, stale, missing, or unchecked.
- Keep ConsultOps, Excerpa, and broader Koho context separated.
- Use `Read Next` only for the next source to inspect, not a work plan.

## Boundaries

- No endpoint probes.
- No external messages.
- No deploys.
- No database writes.
- No repo mutations.
- No runtime sync.
- No client-facing output.
- No workflow instructions.
- No authority changes.
