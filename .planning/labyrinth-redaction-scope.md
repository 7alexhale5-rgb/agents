---
date: 2026-05-20
status: implemented
title: Labyrinth plugin-scoped redaction
---

# Labyrinth Plugin-Scoped Redaction

## Summary

Close the pending Labyrinth redaction decision by keeping Hermes global
redaction off and forcing redaction only in the Labyrinth dashboard plugin
process.

## Runtime Breadcrumb

Labyrinth remains runtime-only. Its source of execution lives at:

`~/.hermes/plugins/hermes-labyrinth/dashboard/plugin_api.py`

The agents repo does not vendor the plugin. The versioned source of truth for
the decision is:

`_meta/decisions/2026-05-20-labyrinth-redaction-scope.md`

## Decision Shape

- Do not set global `security.redact_secrets: true`.
- Do not change Hermes core.
- Do not change profile configs.
- Set `HERMES_REDACT_SECRETS=true` inside the Labyrinth dashboard plugin before
  `agent.redact` can be imported.
- Keep the `prettyfly-fleet` plugin-scoped redaction precedent intact.

## Verification

- Static parse of Labyrinth `plugin_api.py`.
- Clean subprocess redaction smoke for dummy `sk-ant-*`, `ghp_*`, and `xoxb-*`
  strings.
- Dashboard health check for Labyrinth.
- `prettyfly-fleet` meta check still reports redaction enabled.
