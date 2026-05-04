# Codex Handoff — 2026-05-04T21:04:45.029Z

## Branch

- Branch: `main`
- Base: `origin/main`
- Staged workflow files: 0
- Staged source/test files: 1
- Staged generated artifacts: 0

## Staged Source / Test Files

- `CHANGES_FOR_REVIEW.md`

## What this handoff actually covers

This handoff is the marker for the **prior 4 commits** (Phase 0 scaffold + Phase 1 foundation + Phase 1.5 LAIK MCP / VanClief / Honcho), not the staged `CHANGES_FOR_REVIEW.md` file. Codex should review the diff `dd775ab..02d5b79` and especially the LAIK MCP wrapper (Phase 4.5 fusion entrypoint).

## Commits in scope

- `dd775ab` — Phase 0 scaffold (33 dirs, 55 tracked files, agents/ monorepo skeleton)
- `d2677b6` — Phase 0 seed content (README, CLAUDE.md, ORG-CHART, ROUTING-TABLE, ADR-001, .gitignore)
- `0462724` — Phase 1 foundation (personal profile + scripts + 4d-senses MCP + voice-loop skill + email-triage SKU full marketplace package)
- `02d5b79` — Phase 1.5 + LAIK MCP + VanClief (26 files, 2,613 insertions)

## Tests run

- **4d-senses MCP smoke test:** PASS — `node mcp-servers/4d-senses/smoke.js` returns 5 tools, status call returns valid JSON, latest vision report detected at `/tmp/video-intelligence/5c7bfe16f2e8`
- **LAIK MCP smoke test:** PASS — `mcp-servers/laik/.venv/bin/python mcp-servers/laik/smoke.py` returns server v1.27.0, 8 tools listed, `laik_status` returns valid JSON with `ok: true`
- **LAIK API verification:** confirmed `kit.retrieval.pipeline.HybridRetriever(tenant).search()` + `kit.orchestrator.react_loop.run_query()` + `kit.orchestrator.tools.MCPToolbox.{propose,confirm,reject,execute,read_tool_names,write_tool_names}` all present and importable
- **bash scripts/bootstrap-profile.sh vanclief:** PASS — kebab-case validated, sub-tree scaffolded, AGENTS.md symlink created
- **No npm test / pytest run** — wrapper has no unit tests yet (smoke tests are the contract)

## Tests NOT run (intentional or pending)

- Honcho `docker compose up` — Docker daemon not running on this laptop today; deferred
- LAIK MCP exercised against real ConsultOps tenant — would touch prod PG; deferred to operator-driven probe
- VanClief runtime mirror via `hermes profile create vanclief && sync-profile.sh push vanclief` — deferred, Hermes runtime hasn't seen the new profile yet
- Telegram bot pairing — needs BotFather session, operator action

## Risks worth Codex's hardest look

1. **LAIK MCP wrapper API drift.** The wrapper imports `HybridRetriever`, `react_loop.run_query`, `MCPToolbox` from LAIK by name. If LAIK refactors these (rename, signature change), the MCP breaks silently until called. Mitigation: smoke.py exercises status (cheap) but not the actual calls. **Recommended:** add a per-call signature-introspection check at startup, OR pin LAIK version via a marker file.

2. **propose-not-execute integrity.** The wrapper exposes `laik_propose_mutation` + `laik_confirm_mutation` as separate tools. Nothing in the wrapper code prevents an LLM from calling both back-to-back without operator approval. **Mitigation depends on `MCPToolbox.confirm()`** rejecting un-approved or LLM-originated approver_ids — Codex should verify LAIK's implementation enforces this server-side, not just by convention.

3. **`read_only_by_default` for VanClief is documentation-only.** The manifest carries the flag and `_meta/decisions/2026-05-04-vanclief-world-model-audit.md` describes the rule, but no runtime enforcement. The first time VanClief tries to write to another profile's MEMORY.md, nothing actually stops it. **Recommended:** add a Hermes guardrail (or a sense-15-intuition pre-tool hook) that blocks writes outside the profile's own directory tree.

4. **Cross-tenant leak via LAIK MCP if `LAIK_TENANT` env-var is wrong.** The wrapper validates `tenant ∈ list_tenants()` but doesn't validate that the _caller's profile_ is authorized for that tenant. A misconfigured `personal/config.yaml` could attach the LAIK MCP with `LAIK_TENANT=consult-ops` and start reading ConsultOps prod from the personal profile. **Mitigation:** add a tenant-allowlist check in profile config + per-profile JWT scoping.

5. **AGPL Honcho contagion.** Phase 6 ships an on-prem option at Scale tier ($9,999/mo). The runbook says "ships only with commercial Honcho license bundled" but there's no CI gate that enforces it. **Recommended:** add a publish-time check that refuses to flip `manifest.publish: true` if any SKU declares Honcho-bundled.

6. **VanClief cron schedule conflicts.** Sunday Brief at 18:00 ET, world-model audit at 16:00 ET, monthly Research Drop at 09:00 ET on first Sunday of month. The audit must finish before the brief composes. Currently the schedule has 2-hour gap which should be sufficient, but no enforcement of the dependency. **Recommended:** make the brief explicitly depend on the audit's output JSON, fail loudly if missing.

7. **Generated artifacts hygiene.** `mcp-servers/4d-senses/package-lock.json` is committed; `mcp-servers/laik/.venv/` is gitignored. Consistent with norms but worth confirming with Codex.

## Intended commit subject

(prior commit `02d5b79` is already on disk; this handoff documents post-hoc) — if a follow-up commit is recommended, the subject would be:

`fix(laik-mcp): tenant-allowlist + read-only enforcement + signature-introspection`

scoped to Codex's recommended remediations from items 1–4 above.

---

## Recommended Codex review depth

Run `$staged-review` with focus on `mcp-servers/laik/server.py` and `_meta/decisions/2026-05-04-vanclief-world-model-audit.md`. The risks list is the agenda.

---

## Run the Codex review

In Codex (or this Claude session via `codex-plugin-cc`), run:

```
$staged-review              # specialist review (full review checklist)
/codex:review               # generic review
/codex:adversarial-review   # design-challenge review
```

Default sandbox for review: `--sandbox read-only --ask-for-approval on-request`.
