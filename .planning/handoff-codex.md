# Codex Handoff — 2026-05-06T16:47:13.384Z

## Branch

- Branch: `main`
- Base: `origin/main`
- Staged workflow files: 7
- Staged source/test files: 23
- Staged generated artifacts: 0

## Staged Workflow Artifacts

- `.planning/handoff-codex.md`
- `.planning/phase-4-7-prettyfly-runtime/PLAN.md`
- `.planning/phase-4-7-prettyfly-runtime/STATUS.md`
- `.planning/phase-4-7-prettyfly-runtime/baseline/HERMES_BASELINE.md`
- `.planning/phase-4-7-prettyfly-runtime/feature-usage/HERMES_FEATURE_USAGE.md`
- `docs/migration-runbook.md`
- `.planning/phase-4-7-prettyfly-runtime/HANDOFF-2026-05-06.md`

## Staged Source / Test Files

- `_meta/decisions/2026-05-04-adopt-hermes.md`
- `_meta/decisions/2026-05-05-litellm-routing-stack.md`
- `_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md`
- `_meta/runbooks/hermes-commit-digests/2026-05-06.md`
- `marketplace/manifests/email-triage/eval-suite/.gitignore`
- `marketplace/manifests/email-triage/eval-suite/promptfooconfig.yaml`
- `marketplace/manifests/email-triage/eval-suite/runs/2026-05-04-W1.md`
- `marketplace/manifests/email-triage/eval-suite/runs/_nightly-history.tsv`
- `mcp-servers/laik/SPEC.md`
- `ops/audit/STATUS.md`
- `pf-runtime/SPEC.md`
- `pf-runtime/docs/ADAPTER_PLUGIN_INTERFACE.md`
- `pf-runtime/docs/MEMORY_LIFECYCLE.md`
- `pf-runtime/docs/SKILL_SELF_GEN_BOUNDS.md`
- `pf-runtime/pf_runtime/__init__.py`
- `pf-runtime/pf_runtime/stubs/__init__.py`
- `pf-runtime/pf_runtime/stubs/spec_stubs.py`
- `pf-runtime/pyproject.toml`
- `scripts/hermes-commit-watcher.sh`
- `scripts/hermes-feature-audit.sh`
- `tests/__init__.py`
- `tests/profile_dir_contract.py`
- `tests/spec_self_consistency.py`

## Tests run

- `python3 -m ruff check pf-runtime/` → PASS (all checks passed)
- `python3 -m mypy --strict pf-runtime/pf_runtime/` → PASS (no issues)
- `PYTHONPATH=pf-runtime python3 tests/spec_self_consistency.py` → PASS (4/4 contracts)
- `python3 tests/profile_dir_contract.py` → PASS (13/13 profiles, 0 Hermes failures, 0 PF Runtime failures)
- `bash scripts/hermes-feature-audit.sh` → all 13 profile rows populated (was 1/13 in prior pass)

## Risks

This pass applies the 16-fix manifest from the prior `/review-stack --deep --audit` (1 critical + 8 high + 7 medium across 6 perspectives + Codex). No production code is touched; the diff is design specs, contract tests, and ops scripts. Risk surface to re-review:

- **LAIK MCP boundary** (status now DRAFT, not "locked"): `caller_profile_slug` + JWS `session_token` added to all tenant-scoped tools (§3–§6), `confirmer_user_id` replaced with admin-UI-signed `approval_token` (proposal_id, confirmer, expiry, nonce), `mutation_proposals` RLS-by-tenant_id documented with `SET LOCAL laik.session_tenant`, cross-tenant + replay assertions added to `tests/laik_mcp_contract.py` test surface. Sign-off blocked on Phase 4.5 lead.
- **ADR-006 / runbook / PLAN.md sync**: 5-gate cutover list is now identical across all three docs (Promptfoo Wilson lower-CI per profile, Ragas ≥ baseline – 0.02, per-profile real-job execution, p95 latency + concurrent throughput, zero P0). Cost ±10% replaced with latency+throughput per skeptic-finding-4. Kanban store moved from SQLite to Postgres in ADR-006 sub-phase 4.7.4 row + runbook (Tier 2 buffer remains SQLite — explicit note added).
- **PF Runtime SPEC**: §Module layout note documents kebab-vs-snake project-vs-package split (`pf-runtime/` filesystem dir, `pf_runtime/` Python package, `PYTHONPATH=pf-runtime`). Tool ABC dispatcher contract specifies JSONSchema arg validation before `invoke()`; `ToolValidationError` surface added.
- **Stub hygiene**: `Channel.receive` now `async def` (was sync `def` returning AsyncIterator — inconsistent with SPEC.md). `Message` / `InboundMessage` / `OutboundMessage` are now `@dataclass(frozen=True)`.
- **Pre-work scripts**: `hermes-feature-audit.sh` profile iteration bug fixed (find on missing `skills/` dir tripped errexit through pipefail in command substitution); rerun captures all 13 profiles. `hermes-commit-watcher.sh` refuses symlinked digest dir. `tests/profile_dir_contract.py` regex-validates profile.name as kebab-case ASCII before subprocess call.
- **PLAN.md G1 clarification**: dedicated shadow workspace `personal-baseline/` with isolated LiteLLM key alias + Langfuse project; live Phase 1 personal profile is unaffected.

Pass criterion for this re-review: ≤2 critical findings = 4.7.0 gate cleared, then `/commit` + `/ship` + `/compound`.

## Intended commit subject

`chore(phase-4-7): apply 16-fix manifest from review-stack pre-work`

---

## Run the Codex review

In Codex (or this Claude session via `codex-plugin-cc`), run:

```
$staged-review              # specialist review (full review checklist)
/codex:review               # generic review
/codex:adversarial-review   # design-challenge review
```

Default sandbox for review: `--sandbox read-only --ask-for-approval on-request`.
