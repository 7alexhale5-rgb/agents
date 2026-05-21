# Handoff: capability consolidation — Phases 4.8 + 4.9 shipped

**Date**: 2026-05-20
**Session**: Zapier MCP verdict (+ Magica) and prettyfly-fleet operator plugin
**Project**: agents (`~/Projects/agents/`)

## What Was Done

- Shipped Phase 4.8 ADR at [`_meta/decisions/2026-05-20-zapier-mcp-verdict.md`](../_meta/decisions/2026-05-20-zapier-mcp-verdict.md). Verdict: **LIMITED-SCOPE** adoption of Zapier MCP for Gmail draft creation, scoped to a Marin pilot with per-brand servers and a Create-Draft-only action allow-list. Magica added per Alex's request and rejected as wrong primitive.
- Shipped Phase 4.9 plugin at `~/.hermes/plugins/prettyfly-fleet/dashboard/` — read-only Hermes dashboard tab with 4 panels (profiles, events, approvals, crons). Symlinked into `~/.hermes/profiles/personal/plugins/`. Versioned breadcrumb at [`_meta/decisions/2026-05-20-prettyfly-fleet-plugin.md`](../_meta/decisions/2026-05-20-prettyfly-fleet-plugin.md).
- Both ADRs committed in `6c97eee` on `main`.

## Current State

- Hermes dashboard running on http://127.0.0.1:9119 with the plugin mounted at `/fleet`.
- All 5 plugin routes return 200 with real data or graceful typed errors.
- Assets serve cleanly: `index.js` 14,369b, `style.css` 8,605b.
- Redaction is forced on in the plugin process (`HERMES_REDACT_SECRETS=true` at plugin import). Verified masking of `xoxb-`, `sk-ant-`, `ghp_` tokens.
- `/events/recent` and `/approvals/pending` show graceful `PFOS unreachable: RuntimeError` until `HERMES_AGENT_EVENTS_TOKEN` is set in the dashboard process env.
- Commit `6c97eee` not yet pushed.
- Honcho 3-session observation window started today; gates on next 3 Atlas weekly briefs.

## What's Next

1. Alex visually confirms `http://127.0.0.1:9119/fleet` renders the 4-panel grid in his browser.
2. Alex completes the Zapier MCP pre-pilot UI check — verify Gmail "Create Draft" and "Send Email" are independently selectable as MCP actions.
3. If (2) passes, write Phase 4.8.1 file-level plan to wire Zapier MCP into Marin (`marin.gmail_create_draft` shim + contract + eval).
4. Push `6c97eee` to `origin/main` when ready.
5. Decide on Labyrinth global redaction-toggle (still pending from Wave 1).
6. After 3 Atlas weekly briefs ship with Honcho on, run the Honcho acceptance gate from `2026-05-20-honcho-peer-card-atlas.md`.

## Key Decisions

- **Zapier LIMITED-SCOPE, not full Adopt.** Framework arithmetic says Adopt (hard gates + 6/7 medium); the downgrade is policy — wants the 4-readout Marin pilot to clear before fleet rollout, and wants UI verification that Gmail Create-Draft / Send-Email separate before the pilot starts.
- **Magica rejected for THIS question, flagged for separate eval.** Wrong primitive for Gmail drafts; potentially right for Quill/Stet content-production pipelines.
- **Plugin is runtime-only.** Lives at `~/.hermes/plugins/prettyfly-fleet/`, no versioned mirror in the agents repo. Same pattern as `hermes-labyrinth`. The `_meta/decisions/` ADR is the git-tracked breadcrumb.
- **Plugin-scope redaction toggle.** `os.environ.setdefault("HERMES_REDACT_SECRETS", "true")` before importing `agent.redact` forces redaction-on in the dashboard process only.
- **Use `get_default_hermes_root()` not `get_hermes_home()`.** The dashboard runs in profile scope (`~/.hermes/profiles/personal`), but canonical state files live at the root.

## Constraints & Gotchas

- **Plugin adds require dashboard restart.** `_mount_plugin_api_routes()` runs only at startup. Procedure: `~/.local/bin/hermes dashboard --stop && ~/.local/bin/hermes dashboard --no-open --port 9119 &`.
- **Plugin asset URL is `/dashboard-plugins/<name>/dist/...`, not `/api/dashboard/plugins/<name>/dist/...`.** The latter returns the SPA fallback (404-shaped HTML).
- **Per-profile rung is hardcoded in `plugin_api.py`.** When a profile graduates, update `PROFILE_RUNG` dict. YAGNI on discovery until 10+ profiles.
- **PFOS endpoints (`/events/recent`, `/approvals/pending`) need `HERMES_AGENT_EVENTS_TOKEN` in dashboard env** to show live rows. Otherwise the typed `PFOS unreachable` error renders in the panel — which is the intended graceful-failure shape.

## Files Modified This Session

- `_meta/decisions/2026-05-20-zapier-mcp-verdict.md` — NEW, committed in `6c97eee`
- `_meta/decisions/2026-05-20-prettyfly-fleet-plugin.md` — NEW, committed in `6c97eee`
- `~/.hermes/plugins/prettyfly-fleet/dashboard/manifest.json` — NEW (runtime)
- `~/.hermes/plugins/prettyfly-fleet/dashboard/plugin_api.py` — NEW (~280 LOC FastAPI)
- `~/.hermes/plugins/prettyfly-fleet/dashboard/dist/index.js` — NEW (~290 LOC React)
- `~/.hermes/plugins/prettyfly-fleet/dashboard/dist/style.css` — NEW (~270 LOC)
- `~/.hermes/profiles/personal/plugins/prettyfly-fleet` — NEW symlink
