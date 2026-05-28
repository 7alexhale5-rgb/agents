---
date: 2026-05-22
type: decision
project: agents
tags: [adr, hermes, dashboard, webui, fleet, labyrinth, pfos, yagni, sine]
status: accepted
supersedes:
  - 2026-05-21-hermes-web-ui-agentic-angle handoff direction to build PFOS /agents workbench
related_adrs:
  - 2026-05-18-hermes-pfos-event-contract.md
  - 2026-05-20-prettyfly-fleet-plugin.md
  - 2026-05-20-labyrinth-redaction-scope.md
---

# ADR: Hermes WebUI Is The Primary Agent Workbench

## Decision

Freeze PFOS as the agent workbench path.

Hermes WebUI at `http://127.0.0.1:9119` is the primary operating surface for the
PrettyFly Hermes fleet. PFOS remains a read-only evidence and approval-history
backend through the existing `agent_events` contract, but no new PFOS
`/agents/workbench`, proxy, embedded Hermes shell, or copied dashboard should be
built unless a later ADR reverses this decision.

## Operating Split

Use existing Hermes surfaces instead of inventing another cockpit:

| Surface | Job |
| --- | --- |
| Fleet | Read-only operator rail: gateway health, active roster, caps, recent events, pending approvals, cron state, and next action. |
| Labyrinth | Journey, crossing, tool, cost, and failure observability. |
| Sessions | Conversation/run review. |
| Logs | Gateway, plugin, and runtime diagnostics. |
| Profiles | Runtime inventory and drift inspection; not the curated roster source of truth. |
| Config / Keys / Plugins | Admin-only controls. |

The curated fleet roster remains `CLAUDE.md` plus Fleet doctrine. The raw Hermes
Profiles page may show archived or drifted runtime profiles.

## First 1% Slice

Patch the existing runtime-only `prettyfly-fleet` dashboard plugin with a small
read-only Ops rail:

- expose `gateway_state`, `gateway_running`, exact failure reason, and update time;
- detect stale Slack app-token scoped-lock records without deleting them;
- show native links to Fleet, Labyrinth, Logs, Config, Keys, and Profiles;
- replace misleading `codex` roster emphasis with `technical-operator`;
- keep dangerous actions out of the UI.

The plugin stays runtime-only at `~/.hermes/plugins/prettyfly-fleet/`. This ADR
is the versioned breadcrumb.

## Constraints

- No kill button.
- No token editor.
- No profile mutation.
- No approval execution.
- No new database, auth layer, app shell, or PFOS proxy.
- No Hermes runtime bump; stay pinned to v0.12.0 unless a security fix forces it.

## Why This Passes The Bar

- **Karpathy:** one visible operational truth in the live workbench beats a
  speculative platform. The first slice is successful when Alex can open Fleet
  and know whether Hermes is usable and what needs attention next.
- **VanClief:** this audits and corrects the operating world model instead of
  adding another one. Fleet summarizes; Labyrinth explains.
- **YAGNI:** no new cockpit.
- **SOLID:** each Hermes surface keeps one clear job.
- **SINE:** stale PFOS workbench direction is cut from active doctrine.
- **KISS:** one ADR, one plugin route, one small UI rail.
- **DRY:** gateway health comes from Hermes runtime state, not a second health
  model.

## Current Blocker

The personal-profile gateway reports:

`slack: Slack app token already in use (PID 863). Stop the other gateway first.`

Local inspection shows PID `863` is macOS `ctkahp`, not Hermes, and PID `1285`
from another scoped-lock record is gone. Treat those Slack app-token scoped-lock
files as stale only after verifying the live PID state, then remove only those
stale Hermes lock files and restart the gateway.
