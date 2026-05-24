---
date: 2026-05-24
type: decision
project: agents
tags: [adr, hermes, slack, gateway, authority, atlas-ceo, personal, comms-triage, composio]
status: accepted
related_adrs:
  - 2026-05-05-slack-ecosystem-pivot.md
  - 2026-05-22-hermes-webui-primary-workbench.md
  - 2026-05-23-deprecate-pfos-emitter-from-profile-doctrine.md
---

# ADR: Active Slack Gateway Policy For Hermes

## Decision

Only two Hermes profiles may run active Slack gateways right now:

| Profile | Allowed state | Boundary |
| --- | --- | --- |
| `personal` | Active Slack gateway allowed | Personal Hermes runtime only. No policy authority over business profiles. |
| `atlas-ceo` | Active Slack gateway allowed | Alex DM only; advisor/proposer authority only. No public-channel posting, slash commands, file sends, third-party outbound, or autonomous execution. |

Every other active roster profile is Slack-disabled until a separate profile gate
and ADR approve it:

- `marin`
- `quill`
- `stet`
- `technical-operator`
- `codex`
- `morning-logs`
- archived profiles under `hermes/_archive/2026/`

## Operating Rules

1. A profile may be connected to Slack only when its versioned config, runtime
   state, and doctrine all agree on the same channel boundary.
2. Slack token ownership must be verified with local redacted fingerprints only.
   Never commit raw Slack tokens, paste them into reports, include them in
   screenshots, or preserve them in operator artifacts.
3. The dashboard Fleet and Labyrinth surfaces may report gateway state, but they
   do not grant new channel authority.
4. Atlas Slack activity remains DM-only until a later promotion decision cites
   the Atlas rung-4 packet and any required live smoke evidence.
5. Adding another active Slack gateway requires a new dated ADR or an amendment
   that names the profile, allowed Slack surface, approval boundary, rollback,
   and verification evidence.

## Comms Triage / Composio Slack Scope

The `personal` Comms Triage dashboard plugin may remain enabled while its
runtime access is constrained to the exact 26 allowlisted read-only Composio MCP
tools verified in the May 24 repair receipt. This plugin has no posting,
workflow, public-channel, Atlas, or higher-trust authority.

The underlying Composio-managed Slack OAuth grant still advertises broad
write-capable Slack scopes. That is accepted only as a residual risk at the
current read-only runtime boundary, not as precedent for expanding trust.

Before Comms Triage receives any higher authority, the Slack side must move to a
truly least-privilege OAuth app or an equivalent Composio configuration that can
prove strict Slack scope control.

## Verification

The current allowed live state is:

- `ai.hermes.gateway-personal` running with Slack connected.
- `ai.hermes.gateway-atlas-ceo` running with Slack connected.
- Comms Triage re-enabled in the `personal` dashboard with exactly 26
  allowlisted read-only MCP tools exposed.

This policy intentionally does not expand authority. It records the current
allowed state so future dashboard, launchd, or Slack-token drift is visible.

## Rollback

If either allowed gateway behaves outside its boundary:

1. Stop that profile's launchd gateway.
2. Remove or rotate the affected Slack token from the profile runtime env.
3. Record the incident in the operator artifact or relevant profile changelog.
4. Require fresh smoke evidence before reconnecting Slack.
