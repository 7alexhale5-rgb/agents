# Codex Handoff — 2026-05-07T03:58:28.496Z

## Branch
- Branch: `main`
- Base: `origin/main`
- Staged workflow files: 4
- Staged source/test files: 10
- Staged generated artifacts: 0

## Staged Workflow Artifacts
- `.planning/handoff-codex.md`
- `.planning/phase-4-7-prettyfly-runtime/CUTOVER_C_PLAYBOOK.md`
- `.planning/phase-4-7-prettyfly-runtime/STATUS.md`
- `docs/migration-runbook.md`

## Staged Source / Test Files
- `.gitignore`
- `hermes/profiles/personal/CLAUDE.md`
- `hermes/profiles/personal/manifest.json`
- `pf-runtime/pf_runtime/__main__.py`
- `pf-runtime/pf_runtime/config.py`
- `pf-runtime/pf_runtime/memory/__init__.py`
- `pf-runtime/pf_runtime/memory/tier2_buffer.py`
- `pf-runtime/pf_runtime/runtime/loop.py`
- `pf-runtime/pf_runtime/runtime/model_adapter.py`
- `pf-runtime/pyproject.toml`

## Collision Context — Untracked / Skipped

These files exist in the working tree but were left unstaged (use `--include <path>` if they belong to this slice):

- `pf-runtime/docs/CLAWS_ROLE_MAP.md`
- `pf-runtime/pf_runtime/channels/__init__.py`
- `pf-runtime/pf_runtime/channels/adapter_base.py`
- `pf-runtime/pf_runtime/channels/slack.py`
- `pf-runtime/pf_runtime/runtime/gateway.py`
- `pf-runtime/tests/__init__.py`
- `pf-runtime/tests/conftest.py`
- `pf-runtime/tests/test_channel_abc_lifecycle.py`
- `pf-runtime/tests/test_channel_registry.py`
- `pf-runtime/tests/test_gateway_reconnect.py`
- `pf-runtime/tests/test_slack_channel.py`

## Tests run

_Fill in: `npm run lint` / `npm run test` / `npm run build` / Playwright / RLS probe_

## Risks

_Fill in: RLS, tenant scope, telemetry, missing tests, generated-artifact hygiene, etc._

## Intended commit subject

_Fill in: `feat(scope): …` / `fix(scope): …` / `chore(scope): …` ≤72 chars_

---

## Run the Codex review

In Codex (or this Claude session via `codex-plugin-cc`), run:

```
$staged-review              # specialist review (full review checklist)
/codex:review               # generic review
/codex:adversarial-review   # design-challenge review
```

Default sandbox for review: `--sandbox read-only --ask-for-approval on-request`.
