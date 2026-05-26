---
profile: koho-ops
pattern: ConsultOps Pulse
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
propose_write_contract_added: false
private_payload_redacted: true
---

# ConsultOps Pulse v2

Mode: Koho-Ops Rung 1 manual read-only skill run using `consultops-pulse`. No production probes, sends, runtime sync, deploys, database writes, Koho repo mutations, SendPilot calls, Slack messages, email actions, workbook routing, workbook writeback, proposal jobs, or Supabase mutations occurred.

## Current Answer

Koho-Ops can now repeat the ConsultOps Pulse workflow from inside the Hermes profile shape, but it should stay Rung 1.

The new proof in this receipt is not a client-side production proof. It is a Hermes profile proof: `consultops-pulse` exists, its required reads are usable, and the Pulse can be generated from profile docs, ConsultOps Pulse v0, Koho/ConsultOps wiki context, and current read-only repo status.

ConsultOps itself still reads as stable for Marc-facing proof: the ConsultOps repo is clean and synced with `origin/main`, with HEAD at `9bbc4e1 feat: ship supervised Marc readiness foundation`. Process-automation remains related backlog, not clean ConsultOps truth, because it is still ahead of origin with local modified and untracked work.

## Ready Proof

| Proof area | Current signal | Source |
| --- | --- | --- |
| Profile-local workflow | `consultops-pulse` is available as a Koho-Ops skill and defines the required reads, output headings, Rung 1 boundaries, and verification checklist. | `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/skills/consultops-pulse.md` |
| Koho-Ops route | `CLAUDE.md` routes ConsultOps Pulse work to `consultops-pulse` and keeps the profile at Rung 1 with no propose-write tool. | `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/CLAUDE.md` |
| Doctrine | Koho-Ops doctrine says receipts and current repo state outrank memory, ConsultOps and Excerpa stay separated, and any sends, production probes, deploys, runtime sync, or DB writes stop at read-only planning. | `/Users/alexhale/Projects/agents/hermes/profiles/koho-ops/DOCTRINE.md` |
| First source packet | ConsultOps Pulse v0 remains the seed packet and says ConsultOps is ready for a narrow supervised Marc move, not wider automation. | `/Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md` |
| Koho wiki | Koho wiki identifies ConsultOps as Alex-owned inside the Koho partnership and separate from Excerpa. | `/Users/alexhale/Projects/memory-vault/wiki/koho.md` |
| ConsultOps wiki | ConsultOps wiki marks ConsultOps as an active Koho client operations platform and a first-priority memory silo. | `/Users/alexhale/Projects/memory-vault/wiki/consultops.md` |
| ConsultOps repo | `main...origin/main`, clean, HEAD `9bbc4e1 feat: ship supervised Marc readiness foundation`. | `/Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13` |
| Process-automation | `main...origin/main [ahead 1]` with modified worker/test files and untracked planning, Playwright, scoping, and test artifacts. | `/Users/alexhale/Projects/koho/process-automation` |

## Approval Needed

| Candidate Hermes move | Decision needed | Safe shape |
| --- | --- | --- |
| Keep Rung 1 and use manual readouts | Decide that manual `_inbox/koho-ops/` receipts are enough for the next few Koho pulses. | Continue generating committed Markdown receipts from the skill, with no runtime sync and no write tool. |
| Promote toward Rung 2 design | Decide whether Koho-Ops should get a Hermes-local propose-write contract next. | Plan `koho_ops.report.propose` or an equivalent local-only receipt contract, with output locked to `_inbox/koho-ops/` and no external sends. |
| Keep ConsultOps recommendation separate | Decide whether client-side Marc day-one proof should remain a ConsultOps delivery move outside this Hermes slice. | Treat Marc day-one proof as a downstream ConsultOps option, not as this profile capability move. |

## Do Not Enable Yet

- Do not enable production probes.
- Do not enable sends or external-send preparation.
- Do not enable Slack, email, LinkedIn, calendar, SendPilot, SmartLead, or Waalaxy actions.
- Do not enable runtime sync for `koho-ops`.
- Do not deploy.
- Do not write databases.
- Do not mutate Koho repos.
- Do not start proposal jobs.
- Do not enable workbook routing or workbook writeback.
- Do not add `koho_ops.report.propose` or any propose-write contract in this skill-run slice.
- Do not treat process-automation local backlog as clean ConsultOps truth.
- Do not treat Excerpa CLM review readiness as a ConsultOps operating rail.

## Repo And Source State

### Agents

```text
Path: /Users/alexhale/Projects/agents
Branch: codex/hermes-webui-first-1-percent...origin/codex/hermes-webui-first-1-percent
Tracked state: synced with origin before this v2 file was created
Local note: _inbox/koho-ops/2026-05-25-consultops-pulse-v1.md is untracked local residue and was not read as authority, edited, staged, or committed by this skill run.
Tracked prior readout: _inbox/koho-ops/2026-05-26-consultops-pulse-v1.md already exists, so this skill-run proof uses v2.
```

### Memory Vault

```text
Strict wiki validation: failed because wiki/ableton-mcp.md is stale relative to /Users/alexhale/.codex/config.toml.
Maintenance queue: wiki health score 96/100; verdict usable, with unrelated Ableton MCP trust defect.
Koho and ConsultOps pages: available and usable, but older than ConsultOps Pulse v0.
Interpretation: use Koho/ConsultOps wiki for durable relationship context, and let ConsultOps Pulse v0 plus current repo status carry newer operating truth.
```

### ConsultOps

```text
Path: /Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13
Branch: main...origin/main
Status: clean
Recent commits:
9bbc4e1 feat: ship supervised Marc readiness foundation
e55fbfb feat: add safe foundation production proof runner
754d707 feat: harden lead company backfill previews
9c0ed58 refactor: retire legacy company matching surface
5c60e94 docs: plan sanitary workflow certification
cba161e feat: harden Marc supervised operator readiness
2d56942 docs: add Marc day-one readiness contracts
49d1744 fix: isolate notification realtime channels
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

## Next 1% Move

Decide whether Koho-Ops should graduate from manual Rung 1 readouts toward a Rung 2 local propose-write contract.

The next Hermes-shaped slice is a plan for a minimal `koho_ops.report.propose` contract or equivalent local-only proposal receipt: input source packet, output path locked to `_inbox/koho-ops/`, redaction expectations, no external channels, and explicit confirmation that runtime sync, production probes, sends, deploys, database writes, and Koho repo mutations remain blocked.

Client-side Marc day-one proof remains a valid ConsultOps delivery recommendation from ConsultOps Pulse v0, but it is not the next Hermes profile capability move.

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
