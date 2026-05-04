# LAIK MCP server — Phase 4.5 fusion entrypoint

Wraps LAIK (Local AI Kit) as a stdio MCP server so any Hermes profile can read company facts (hybrid RAG + SQL tools) and propose-not-execute mutations.

## Why

LAIK is the **company world model layer** in our Company AGI architecture (per `~/Projects/research-vault/research/2026-05-04-company-agi-laik-hermes-fusion.md` §3.2). It's already production-grade for ConsultOps + YEH. The Phase 4.5 fusion strips its FastAPI wrapper and exposes the same primitives over MCP — so every Hermes agent reads grounded facts before answering.

## Architecture

- **Imports LAIK from PYTHONPATH** — does not bundle, does not fork. Operator points `LAIK_ROOT` at their existing `~/Projects/local-ai-kit/` install.
- **Stdio MCP** (per the standard) — Hermes spawns the server per profile; lifecycle bound to the profile.
- **Six tools:** `laik_status`, `laik_list_tenants`, `laik_query`, `laik_sql`, `laik_propose_mutation`, `laik_confirm_mutation`.
- **Read-only by default.** Writes go through LAIK's existing `mutation_proposals` two-phase protocol — never auto-executed.

## Install in a Hermes profile

In `~/.hermes/profiles/<name>/config.yaml`:

```yaml
mcp_servers:
  laik:
    command: python3
    args: ["/Users/alexhale/Projects/agents/mcp-servers/laik/server.py"]
    env:
      LAIK_ROOT: /Users/alexhale/Projects/local-ai-kit
      LAIK_TENANT: consult-ops # or yeh, or whichever tenant this profile reads
```

Then restart the profile: `hermes profile restart <name>`.

## Smoke test

```bash
cd /Users/alexhale/Projects/agents/mcp-servers/laik
python3 smoke.py
```

Expected: tools/list returns 6 tools, `laik_status` returns JSON with `ok: true` and the tenant inventory.

## What it doesn't do

- Doesn't bypass LAIK's Ragas faithfulness gate (0.85 floor) — that's enforced inside the LAIK pipeline.
- Doesn't bypass the cross-repo grant boundary (ADR-0001) — LAIK owns LAIK schema, YEH owns product schema; this MCP only calls into LAIK's existing API surface.
- Doesn't auto-execute mutations — the propose-not-execute pattern is preserved end-to-end.
- Doesn't bundle Honcho or any AGPL code.

## Dependencies

- Python 3.11+
- LAIK installed at `LAIK_ROOT` (default `~/Projects/local-ai-kit/`) with its own venv + Postgres
- `mcp` Python SDK (`pip install mcp`)

## Failure modes

| Symptom                                                 | Likely cause                 | Fix                                                                                         |
| ------------------------------------------------------- | ---------------------------- | ------------------------------------------------------------------------------------------- |
| Server exits with "LAIK_ROOT does not exist"            | Path wrong                   | Set `LAIK_ROOT` env var in profile config.yaml                                              |
| Tool calls return `LAIK pipeline.run_query() not found` | LAIK refactored the API      | Update `server.py` to match LAIK's current entrypoint name                                  |
| Cross-tenant rows in laik_query result                  | RLS misconfigured            | **P0** — halt all profiles via seal-profile.sh, audit PG roles                              |
| Mutation auto-executed without proposal                 | Propose-not-execute bypassed | **P0** — halt, audit `mutation_proposals` and `mutation_audit` tables, file regression test |

## Phase 4.5 rollout sequence

1. Deploy this MCP wrapper to the laptop (smoke-test green).
2. Attach to `personal` profile first (lowest stakes — reads Alex's Obsidian vault, not ConsultOps prod).
3. After 7 days of personal-profile usage, attach to `consultops` and `yeh-ops`.
4. Old LAIK FastAPI service stays read-only for 30-day overlap.
5. After 30 days of zero traffic to FastAPI, decommission.
