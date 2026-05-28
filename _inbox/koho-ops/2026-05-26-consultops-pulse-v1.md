---
profile: koho-ops
pattern: ConsultOps Awareness Pulse
version: v1
generated_at: 2026-05-26
status: superseded_by_awareness_correction
mode: rung_1_read_only_manual
source_packet: /Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md
external_send: false
production_probe: false
runtime_sync: false
deploy: false
database_write: false
koho_repo_mutation: false
private_payload_redacted: true
---

# ConsultOps Awareness Pulse v1

This file supersedes the original May 26 v1 wording. The prior version drifted into workflow instructions. Correct intent: Koho-Ops is a Hermes ear-to-the-ground awareness profile only. It is not used to operate ConsultOps, Koho, Excerpa, or client workflows.

No production probes, sends, runtime sync, deploys, database writes, Koho repo mutations, external messages, workflow actions, proposal jobs, or Supabase mutations occurred.

## Current State

The useful signal is source awareness: Koho-Ops can read profile docs, ConsultOps historical source packets, Koho/ConsultOps wiki context, and repo status to answer "where are we and what changed?"

ConsultOps repo state at the time of this readout was clean and synced with `origin/main`, with HEAD `9bbc4e1`. Process-automation was ahead of origin with local modified and untracked work. Those are status facts only, not workflow priorities.

## Source Updates

| Source | Status signal |
| --- | --- |
| Koho-Ops profile | Rung 1 read-only profile exists in Hermes. |
| ConsultOps Pulse v0 | Historical source packet exists and may be used for context, not as an action plan. |
| Koho wiki | Provides durable relationship context. |
| ConsultOps wiki | Provides durable project context. |
| ConsultOps repo | Clean and synced with origin at the observed commit. |
| Process-automation | Local backlog exists and should be reported as repo state only. |

## Repo And Source State

```text
agents: codex/hermes-webui-first-1-percent...origin/codex/hermes-webui-first-1-percent
ConsultOps: main...origin/main, clean, HEAD 9bbc4e1
process-automation: main...origin/main [ahead 1], with local modified and untracked files
memory wiki: Koho and ConsultOps pages usable; newer receipts should override stale wiki summaries
```

## Stale Or Missing Context

- Older wording in this file treated the profile as workflow-oriented. That is superseded.
- ConsultOps Pulse v0 includes action-oriented recommendations; Koho-Ops must treat them as historical context only.
- This readout did not inspect production systems or external tools.

## Boundaries

- Awareness only.
- No ConsultOps, Koho, or Excerpa operation.
- No production probes.
- No sends.
- No runtime sync.
- No deploys.
- No database writes.
- No Koho repo mutations.
- No workflow instructions.
- No action-authority promotion.

## Next Check

Use the corrected profile shape to produce a clean awareness note that answers only: what sources changed, what repo states changed, what context looks stale, and what source should be checked next.

## Source Basis

- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/CLAUDE.md`
- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/DOCTRINE.md`
- `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/MEMORY.md`
- `/Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md`
- `/Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13`
- `/Users/alexhale/Projects/koho/process-automation`
