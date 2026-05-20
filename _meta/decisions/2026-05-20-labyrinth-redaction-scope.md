---
date: 2026-05-20
type: decision
status: active
tags: [hermes, labyrinth, redaction, dashboard, decision]
parent_plan: ~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md
related_adrs:
  - 2026-05-20-prettyfly-fleet-plugin.md
  - 2026-05-18-hermes-pfos-event-contract.md
supersedes: none
---

# Labyrinth redaction scope

## Decision

Defer a global Hermes redaction toggle. Force secret redaction only inside the
Labyrinth dashboard plugin process by setting `HERMES_REDACT_SECRETS=true` in
`~/.hermes/plugins/hermes-labyrinth/dashboard/plugin_api.py` before
`agent.redact` can be imported.

This mirrors the `prettyfly-fleet` plugin-scoped redaction precedent and closes
the pending Wave 1 Labyrinth redaction decision without changing Hermes core or
profile runtime behavior.

## Rationale

Hermes v0.12 keeps `security.redact_secrets` off by default because global
redaction can corrupt patches, API payloads, and other tool output that happens
to contain fake secret-shaped substrings. That default should remain intact for
agent work.

Labyrinth is different: it renders local trajectory previews and exports
operator-facing reports. Those surfaces should fail closed or redact even when
the broader runtime leaves redaction off. Plugin load order also makes relying
on `prettyfly-fleet` to set the process env fragile; Labyrinth must own its own
redaction toggle.

## Scope

In scope:

- Labyrinth dashboard previews.
- Labyrinth journey/crossing/report output that passes through `_preview()` or
  `_redact()`.
- Runtime-only patch under `~/.hermes/plugins/hermes-labyrinth/`.

Out of scope:

- Global `security.redact_secrets: true` in `~/.hermes/config.yaml`.
- Hermes core redaction changes.
- Per-profile config changes.
- Generic redaction middleware or fleet-wide privacy framework.

## Verification

- `plugin_api.py` parses successfully.
- A clean subprocess imports Labyrinth `plugin_api.py` and confirms dummy
  `sk-ant-*`, `ghp_*`, and `xoxb-*` tokens are masked by `_preview()`.
- Dashboard restart keeps `/api/plugins/hermes-labyrinth/health` healthy.
- `prettyfly-fleet` `/meta` still reports redaction enabled.

## Reversibility

TYPE-2. Remove the one `os.environ.setdefault(...)` line from the Labyrinth
plugin and restart the dashboard. No persisted state or repo-tracked runtime
sync changes are involved.
