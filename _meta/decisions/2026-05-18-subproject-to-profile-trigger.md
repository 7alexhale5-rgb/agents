---
date: 2026-05-18
type: decision
project: agents
tags: [adr, hermes, profiles, subprojects, yagni]
status: accepted
parent_plan: ~/.claude/plans/here-is-what-we-joyful-torvalds.md
---

# ADR: Sub-Project To Profile Trigger

## Decision

A sub-project earns its own Hermes profile only after the work proves it needs durable agent identity.

Create a profile when any one trigger holds for 30 consecutive days:

- revenue is at least `$2k/mo`
- recurring operator time is at least `3hr/week` for four consecutive weeks
- at least `3` paying customers or tenants exist

## Process

When a trigger fires:

1. Write a decision note naming the trigger and evidence.
2. Build the profile from the 11-file contract.
3. Start at rung 1 unless a separate promotion gate says otherwise.
4. Use the same lint, event, eval, and dogfood gates as Atlas and CMO.

## Demotion

If no trigger holds for 90 consecutive days, archive the profile to `hermes/_archive/YYYY/` and demote the work back to a sub-project without profile identity.

## Why

Profiles are expensive because they carry voice, memory, routing, tools, and channel identity. Skills and shared docs are cheaper. This trigger keeps the fleet focused on the `$1M ARR` mission.
