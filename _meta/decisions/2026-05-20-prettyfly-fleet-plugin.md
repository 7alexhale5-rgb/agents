---
date: 2026-05-20
type: decision
status: active
tags: [hermes, plugin, dashboard, observability, prettyfly-fleet, decision]
parent_plan: ~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md
related_adrs:
  - 2026-05-18-hermes-pfos-event-contract.md
  - 2026-05-20-honcho-peer-card-atlas.md
supersedes: none
---

# `prettyfly-fleet` Hermes dashboard plugin — read-only operator view

## Decision

Ship a read-only Hermes dashboard plugin at `~/.hermes/plugins/prettyfly-fleet/` that renders four panels for the PrettyFly operator (Alex): profile roster with daily caps, recent agent events with redacted previews, pending PFOS approvals with link-throughs, and Hermes cron status. The plugin is symlinked into `~/.hermes/profiles/personal/plugins/prettyfly-fleet/` (mirrors the Labyrinth precedent so the personal profile picks it up).

The plugin is **runtime-only — no versioned mirror in the agents repo**, same as `hermes-labyrinth`. The Hermes runtime is the source of truth for plugin code; this ADR is the versioned breadcrumb that records the decision, the file layout, and the operational gates.

## File layout

```
~/.hermes/plugins/prettyfly-fleet/dashboard/
├── manifest.json        # 13 lines — name, tab, entry, css, api
├── plugin_api.py        # ~280 LOC — FastAPI router, 5 routes, in-process cache
└── dist/
    ├── index.js         # ~290 LOC — single-file React via __HERMES_PLUGIN_SDK__
    └── style.css        # ~270 LOC — crimson/bronze/gold rung palette

~/.hermes/profiles/personal/plugins/prettyfly-fleet
    -> /Users/alexhale/.hermes/plugins/prettyfly-fleet   (symlink)
```

## Routes

| Route                                                     | TTL  | Source                                                                                           |
| --------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------ |
| `GET /api/plugins/prettyfly-fleet/profiles`               | 120s | `fleet/limits.json` + `~/.hermes/.emit-counters.json` + profile manifests + PFOS `last_event_ts` |
| `GET /api/plugins/prettyfly-fleet/events/recent?limit=50` | 60s  | PFOS `GET /api/silos/skills/agent-events?limit=N`                                                |
| `GET /api/plugins/prettyfly-fleet/approvals/pending`      | 60s  | PFOS `GET /api/silos/skills/agent-events?status=pending&limit=50`                                |
| `GET /api/plugins/prettyfly-fleet/crons`                  | 60s  | `~/.hermes/cron/jobs.json`                                                                       |
| `GET /api/plugins/prettyfly-fleet/meta`                   | live | env probe (version, redaction state, token presence)                                             |

## Plugin-scope redaction

`plugin_api.py` sets `os.environ.setdefault("HERMES_REDACT_SECRETS", "true")` BEFORE importing `agent.redact`. The redactor snapshots `_REDACT_ENABLED` once at module load (`agent/redact.py:60-64`) and Python module caching means the dashboard process imports it once — so the env flip only forces redaction-on for content this plugin reads in this process. Other Hermes profile processes (Quill drafting, Atlas weekly brief, etc.) keep whatever `security.redact_secrets` they have in their own configs.

This is the workaround documented in the parent plan as the "Wave 1 Labyrinth gate" pattern. It's correct precisely because each profile runs as its own process — a global Hermes runtime toggle would have wider blast radius than we want.

Verified at runtime: `/meta` returns `redact_secrets_enabled: true`, and the redactor masks `xoxb-*`, `sk-ant-*`, `ghp_*` tokens in event previews.

## HERMES_HOME resolution

The dashboard process resolves `HERMES_HOME` to the active profile path (e.g. `~/.hermes/profiles/personal`). The canonical Hermes state files (`.emit-counters.json`, `cron/jobs.json`) live at the **root**, not under any profile. The plugin uses `hermes_constants.get_default_hermes_root()` to unwind the profile suffix; if `HERMES_HOME` ends in `/profiles/<name>`, the helper returns the grandparent — the actual `~/.hermes/`.

## PFOS token wiring

As of 2026-05-20, the dashboard process is launched through the env-scope helper `~/.local/bin/hermes-dashboard-prettyfly`. The helper sources `~/.config/prettyfly-marketing/hermes-tokens.env` as the single credential source, then starts `hermes dashboard --no-open --port 9119` with `HERMES_AGENT_EVENTS_TOKEN` in-process.

PFOS now exposes the narrow bearer read path the plugin already called:

```
GET /api/silos/skills/agent-events?limit=N
GET /api/silos/skills/agent-events?status=pending&limit=50
```

The token row keeps `agent_events:write` and now also carries `agent_events:read`. The read endpoint returns tenant-scoped row metadata with `agent_slug` flattened and JSONB `data` values replaced by key-preserving `[redacted]` placeholders, so Fleet panels can render previews without a raw event-body export.

## Per-profile rung

The Karpathy ladder rung (1=crimson, 2=bronze, 3=gold, 4=olympian) is **hardcoded** in the plugin as a name→int dict. Profile manifests do not carry a rung field; rung is a doctrine concept, not a config primitive. When a profile graduates, update `PROFILE_RUNG` in `plugin_api.py`. YAGNI on building rung-discovery logic until we have 10+ profiles.

## Verification (all gates pass)

1. Static gates ✅
   - `python3 -c "import ast; ast.parse(...)"` — `plugin_api.py` syntax OK
   - `node --check dist/index.js` — JS syntax OK
   - `json.load(manifest.json)` — manifest OK
2. Discovery ✅
   - `curl /api/dashboard/plugins/rescan` then `/api/dashboard/plugins` — `prettyfly-fleet` appears, `source=user`, `has_api=true`
3. Routes ✅ (post dashboard restart)
   - `/meta` returns `{version: 0.1.0, redact_secrets_enabled: true, hermes_home: /Users/alexhale/.hermes}`
   - `/profiles` returns all 5 profiles with rung, tier, daily_cap, today_emit_count
   - `/events/recent?limit=1` returns live PFOS rows with no `error`
   - `/approvals/pending` returns live PFOS pending rows with no `error`
   - `/crons` returns jobs from `~/.hermes/cron/jobs.json` with normalized `last_status`
4. Redaction smoke ✅
   - `xoxb-fake-token-1234567890abcdef` → `xoxb-f...cdef`
   - `sk-ant-api03-fakekey0987654321test` → `sk-ant...test`
   - `ghp_realLookingButFake1234567890` → `ghp_re...7890`
5. Performance ✅
   - `/profiles` p95 = 2ms over 10 sequential calls (gate: <500ms)

## Restart requirement

`_mount_plugin_api_routes()` (in `hermes_cli/web_server.py:3969`) runs only at dashboard startup. Adding a plugin requires:

1. Drop files into `~/.hermes/plugins/<name>/dashboard/`
2. `hermes dashboard --stop`
3. `hermes dashboard --no-open --port 9119 &`

`/api/dashboard/plugins/rescan` is enough for the frontend to discover a new plugin, but the FastAPI routes only mount at process start.

## Reversibility

TYPE-2 — `rm -rf ~/.hermes/plugins/prettyfly-fleet` and restart the dashboard. The personal-profile symlink is dangling at that point; remove it separately. No persisted state survives the uninstall.

## Rollback procedure

1. `rm ~/.hermes/profiles/personal/plugins/prettyfly-fleet`
2. `rm -rf ~/.hermes/plugins/prettyfly-fleet`
3. `~/.local/bin/hermes dashboard --stop && ~/.local/bin/hermes dashboard --no-open --port 9119 &`

## Acceptance (1-week observation)

After 1 week of use, all of these should hold:

1. Plugin remains in `/api/dashboard/plugins` with `source=user`
2. `/profiles` continues to return all 5 profiles with non-null daily_cap values for atlas-ceo / marin / quill / stet
3. At least one PFOS event appears in `/events/recent` (validates the read path against live PFOS)
4. At least one cron job's `last_run_at` becomes non-null (validates the cron read after a scheduled run fires)
5. No redaction false negatives in the events panel — Alex visually confirms no raw token-shaped strings render

If any fail, debug or roll back.

## Related

- Parent plan: [`~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md`](../../.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md)
- Hermes plugin discovery: `~/.hermes/hermes-agent/hermes_cli/web_server.py:3558-4013`
- Plugin SDK precedent (single-file React, no build): `~/.hermes/hermes-agent/plugins/example-dashboard/dashboard/dist/index.js`
- Labyrinth precedent (user plugin + personal symlink): `~/.hermes/plugins/hermes-labyrinth/`
- Redactor (env-snapshot pattern): `~/.hermes/hermes-agent/agent/redact.py:60-64`
- PFOS event endpoint: `hermes/lib/agent_events.py:309-336`
- Fleet limits: [`fleet/limits.json`](../../fleet/limits.json)
