---
profile: koho-ops
pattern: ConsultOps Awareness Pulse
version: v2
generated_at: 2026-05-26
mode: rung_1_read_only_manual_skill_run
skill: hermes/profiles/koho-ops/skills/consultops-pulse.md
source_packet: /Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md
external_send: false
production_probe: false
runtime_sync: false
deploy: false
database_write: false
koho_repo_mutation: false
action_authority: false
private_payload_redacted: true
---

# ConsultOps Awareness Pulse v2

Mode: Koho-Ops Rung 1 manual read-only awareness run using `consultops-pulse`. No production probes, sends, runtime sync, deploys, database writes, Koho repo mutations, external messages, workflow actions, proposal jobs, or Supabase mutations occurred.

This corrected version replaces the earlier workflow-shaped framing. Koho-Ops is not for operating ConsultOps or Koho. Its job is to keep an ear to the ground: current source truth, repo state, freshness, and missing context.

## Current State

Koho-Ops is now framed as a source-awareness profile, not an action profile.

Current source truth says the ConsultOps repo is clean and synced with `origin/main`, with HEAD `9bbc4e1`. Process-automation is still ahead of origin with local modified and untracked work. The memory wiki is usable for durable Koho/ConsultOps context, but newer receipts and current repo status should carry fresher operating truth.

## Source Updates

| Source | Current signal | Use in Koho-Ops |
| --- | --- | --- |
| `consultops-pulse` skill | Exists as a profile-local Rung 1 skill. | Use for awareness notes only. |
| Koho-Ops profile docs | Corrected to say awareness-only, no workflow actions. | Source of profile boundaries. |
| ConsultOps Pulse v0 | Historical read-only packet exists. | Use for context and source lineage, not instructions. |
| Koho wiki | Provides durable relationship context and notes ConsultOps and Excerpa as separate lanes. | Use as background context. |
| ConsultOps wiki | Provides durable project context and notes ConsultOps as active. | Use as background context. |
| ConsultOps repo | Clean and synced at observed HEAD `9bbc4e1`. | Report as repo state only. |
| Process-automation | Ahead of origin with local modified and untracked files. | Report as local backlog state only. |

## Repo And Source State

### Agents

```text
Path: /Users/alexhale/Projects/agents
Branch: codex/hermes-webui-first-1-percent...origin/codex/hermes-webui-first-1-percent
Tracked state before correction: synced with origin
Local note: _inbox/koho-ops/2026-05-25-consultops-pulse-v1.md is untracked local residue and was not edited or staged.
```

### Memory Vault

```text
Strict wiki validation: failed because wiki/ableton-mcp.md is stale relative to /Users/alexhale/.codex/config.toml.
Maintenance queue: wiki health score 96/100; verdict usable, with unrelated Ableton MCP trust defect.
Koho and ConsultOps pages: available and usable, but older than ConsultOps Pulse v0.
Interpretation: use Koho/ConsultOps wiki for durable background, and current repo status for freshness.
```

### ConsultOps

```text
Path: /Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13
Branch: main...origin/main
Status: clean
Observed HEAD: 9bbc4e1
```

### Process-Automation

```text
Path: /Users/alexhale/Projects/koho/process-automation
Branch: main...origin/main [ahead 1]
Tracked changes:
M worker/main.py
M worker/tests/test_fireflies_resolver.py
Untracked:
.planning/proposal-ai-flow-preview.html
.playwright-mcp/
data/scoping/
worker/tests/test_ai_edit.py
worker/tests/test_variable_map_mirror.py
```

## Stale Or Missing Context

- The original Koho-Ops profile language described an operating-agent role. That was wrong and is superseded by this correction.
- Older ConsultOps receipts may contain suggested next steps. Koho-Ops should preserve them as history only.
- This awareness run did not inspect production systems, external tools, databases, Slack, email, or SendPilot.

## Boundaries

- Awareness only.
- No ConsultOps, Koho, Excerpa, or client workflow operation.
- No production probes.
- No sends.
- No runtime sync.
- No deploys.
- No database writes.
- No Koho repo mutations.
- No workflow instructions.
- No action-authority promotion.

## Next Check

Create a small source freshness checklist for Koho-Ops: which wiki pages, receipts, and repo status commands should be read when Alex asks "where are we?" Keep it read-only and make it answer status, not strategy or workflow direction.

## Source Basis

- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/skills/consultops-pulse.md`
- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/CLAUDE.md`
- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/DOCTRINE.md`
- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/MEMORY.md`
- `/Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md`
- `/Users/alexhale/Projects/memory-vault/wiki/koho.md`
- `/Users/alexhale/Projects/memory-vault/wiki/consultops.md`
- `/Users/alexhale/Projects/memory-vault/scripts/memory_hub.py --validate --strict-wiki`
- `/Users/alexhale/Projects/memory-vault/scripts/memory_hub.py --maintenance-queue --dry-run`
- `/Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13`
- `/Users/alexhale/Projects/koho/process-automation`
