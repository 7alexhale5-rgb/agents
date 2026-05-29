---
date: 2026-05-29
type: decision
project: agents
tags: [adr, hermes, profiles, research-scout, topic-intelligence, notebooklm, karpathy-ladder]
status: accepted
related_adrs:
  - 2026-05-18-agent-shape-11-file-contract.md
  - 2026-05-24-hermes-active-slack-gateway-policy.md
  - 2026-05-20-capability-build-sequence.md
plan: ~/.claude/plans/full-swarm-of-agents-wild-manatee.md
---

# ADR: Research Scout Fleet — Continuous Topic Intelligence

## Decision

Add a fleet of dedicated **read-only topic-intelligence scout profiles** to the
Hermes monorepo — one per topic specialty — each built on the Atlas 11-file
contract, each earning rungs via outcome-based graduation gates (rung 1
read-only → rung 2 propose → rung 3 scoped action), exactly as Atlas did.

The four scouts and their topics:

| Scout | Topic | NotebookLM notebook | Feeds |
| --- | --- | --- | --- |
| `hermes-scout` | Hermes Agent runtime | Hermes Runtime `771c0174` | `~/Projects/agents/` + cockpit |
| `cc-scout` | Claude Code + Anthropic | AI Automation & LLMs `988d6e87` | env-global `~/.claude/` |
| `mcp-scout` | Agentic patterns + MCP | AI Agents & Orchestration `a4ca2b00` | cross-project architecture |
| `pkm-scout` | NotebookLM + PKM | Personal Automation `f181b42e` | memory/research-vault workflows |

## Why

Two Jack Roberts videos (Hermes × NotebookLM; "everything Hermes") confirmed an
architecture Alex already owns ~80% of: research-stack already ingests into
NotebookLM, 4d-auto-vision transcribes videos, env-update-sweep runs daily,
`notebooklm-py` holds 12+ topic notebooks. The gap was scheduling, topic-scoping,
and routing — not capability. Dedicated scouts (one specialty each) keep the
signal sharp and let each workflow refine in depth, versus one diluted sweep.

## Build sequence (Karpathy ladder — locked)

- **Phase 0** ✅ (2026-05-29): NotebookLM re-auth + permanent keep-alive bridge
  (`com.prettyfly.notebooklm-keepalive`, every 3 days) + "Hermes Runtime"
  notebook created (`771c0174`) + registered in `research-stack/references/notebook-routing.md`.
- **Phase 1** (this ADR): build `hermes-scout` end-to-end as the reference. Rung 1.
- **Phase 2**: clone the reference to `cc-scout`, `mcp-scout`, `pkm-scout`. Each rung 1.
- **Phase 3**: surfaces — morning-brief + vault (rung 1), PFOS cockpit Intelligence lane, Slack 2-way (rung 2+).
- **Phase 4**: rung-2 graduation per scout (propose tickets into project `.planning/`).

No scout is built before the prior phase's gate holds. No scout earns rung 2+
before its rung-1 gate holds across ≥2 useful weekly digests.

## hermes-scout rung-1 acceptance gate

Live at rung 1 only when, in one run: a digest lands in
`_inbox/hermes-scout/{date}-digest.md` AND ≥1 source is ingested into notebook
`771c0174` AND `scripts/lint-profile.sh hermes-scout` = PASS AND the digest
carries ≥1 CI-rubric verdict with a named target. Promotion to rung 2 requires
the gate to hold across ≥2 consecutive Alex-confirmed-useful weekly digests.

## Authority boundary (all scouts, rung 1)

- Read-only on the world (web, YouTube, GitHub, local repos). Never mutate any repo, deploy, merge, or execute a finding.
- Writes only to `_inbox/<scout>/` + NotebookLM source ingestion into the scout's notebook.
- No channels. Slack is **forbidden at rung 1** per `2026-05-24-hermes-active-slack-gateway-policy.md`; a scout earns Slack via a dated amendment to that ADR after its rung-1 gate holds.
- Every finding cites a source; fabrication of a release/version/capability is the one unrecoverable failure. Every finding carries one CI-rubric verdict + a named target.

## Reuse (SINE/DRY)

`bootstrap-profile.sh`, the Atlas profile shape, `/research-stack` (NotebookLM-wired),
`notebooklm-py`, `wire-fleet-cron.sh`, `fleet/limits.json`, the CI verdict rubric,
`morning-brief`, `lint/validate/sync-profile.sh`. New code per scout = one
`topic-sweep.md` skill + one cron + one fleet-limit row.

## Reversal

Reversible by removing the scout profile dirs + their crons + their `fleet/limits.json`
rows + this ADR. No runtime/schema/contract change; the emitter and gateway are
untouched. The NotebookLM keep-alive launchd is independently useful and stays.

## Cost

Weekly `/research-stack --deep` per scout. Capped via `fleet/limits.json`
(hermes-scout = 2/day) + the CI 10-ingestions/day ceiling. Weekly (not daily)
deep sweeps keep spend bounded.
