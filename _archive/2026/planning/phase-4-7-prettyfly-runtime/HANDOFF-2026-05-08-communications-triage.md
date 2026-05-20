# Handoff: Communications Triage v1 — read/propose runtime foundation

**Date**: 2026-05-08  
**Session**: Codex implementation of unified mail + calendar agent plan  
**Project**: agents (`~/Projects/agents/`)  
**Stack**: build-stack + ops-stack + review-stack  
**Status**: implemented, verified, not staged, not committed

## What Was Done

- Added PF Runtime communications primitives under `pf-runtime/pf_runtime/communications/`:
  - normalized provider/account/message/calendar/action schema
  - Gmail, Microsoft Graph, and HostGator IMAP normalization helpers
  - v1 mutation policy that refuses live application and only allows proposals
  - SQLite `ProposalStore`
  - `communications.propose_action` runtime tool
- Added `pf_runtime/runtime/tool_dispatch.py`:
  - schema-like argument validation before `invoke()`
  - unknown-tool and validation errors
  - repeated same tool+args cycle detection
  - TRACE_SCHEMA-compatible tool-call trace emission without raw args
- Updated `pf_runtime/runtime/loop.py`:
  - no longer ignores `tools`
  - supports JSON envelope tool calls:
    `{"tool_call":{"name":"communications.propose_action","arguments":{...}}}`
  - enforces `max_steps`, model/tool timeouts, interrupts, and cost ceiling
  - injects available tool catalog into the system prompt
- Updated PF Runtime docs:
  - `pf-runtime/SPEC.md` now describes the implemented validation subset
  - `pf-runtime/docs/COMMUNICATIONS_TRIAGE.md` documents the v1 boundary and forbidden scopes/actions
- Added marketplace/profile contracts:
  - new `marketplace/manifests/communications-triage/` SKU with provider matrix, forbidden v1 scopes, proposal-only actions, account registry example, pricing, runbook, SOUL, A2A card
  - personal profile now installs `communications-triage`
  - personal profile docs describe direct-provider mail/calendar triage as read + propose only
  - legacy `email-triage` bumped to `0.2.0`, marked `superseded_by: communications-triage`, and softened from auto-archive/delete to proposal-only language
- Added tests:
  - `pf-runtime/tests/test_communications_schema.py`
  - `pf-runtime/tests/test_tool_dispatch.py`
  - `tests/communications_marketplace_contract.py`

## Current State

- Branch: `main`, `origin/main [ahead 3]`
- Worktree was dirty before this session. Do **not** assume all dirty files belong to this communications slice.
- Pre-existing unrelated dirty files observed before/alongside this work:
  - `CLAUDE.md`
  - `hermes/profiles/atelier/skills/design-audit/SKILL.md`
  - `hermes/profiles/atelier/skills/design-md-author/SKILL.md`
  - `hermes/profiles/atelier/skills/design-stack-run/SKILL.md`
  - `hermes/profiles/atelier/skills/library-curate/SKILL.md`
  - `marketplace/manifests/email-triage/eval-suite/runs/_nightly-history.tsv`
  - `_meta/runbooks/hermes-commit-digests/2026-05-08.md`
- This session intentionally did **not** wire live OAuth, refresh-token storage, IMAP credentials, SMTP, Gmail modify, Graph writes, or calendar writes.
- This session intentionally did **not** touch PFOS repo code; PFOS remains the command/observability plane.

## Communications Slice Files

Primary new/modified files for this slice:

- `pf-runtime/pf_runtime/communications/__init__.py`
- `pf-runtime/pf_runtime/communications/schema.py`
- `pf-runtime/pf_runtime/communications/providers.py`
- `pf-runtime/pf_runtime/communications/policy.py`
- `pf-runtime/pf_runtime/communications/proposal_store.py`
- `pf-runtime/pf_runtime/communications/tools.py`
- `pf-runtime/pf_runtime/runtime/tool_dispatch.py`
- `pf-runtime/pf_runtime/runtime/loop.py`
- `pf-runtime/pf_runtime/runtime/trace.py`
- `pf-runtime/SPEC.md`
- `pf-runtime/docs/COMMUNICATIONS_TRIAGE.md`
- `pf-runtime/tests/test_communications_schema.py`
- `pf-runtime/tests/test_tool_dispatch.py`
- `tests/communications_marketplace_contract.py`
- `hermes/profiles/personal/config.yaml`
- `hermes/profiles/personal/SOUL.md`
- `hermes/profiles/personal/CLAUDE.md`
- `hermes/profiles/personal/skills/communications-triage/SKILL.md`
- `marketplace/manifests/communications-triage/*`
- `marketplace/manifests/email-triage/manifest.json`
- `marketplace/manifests/email-triage/a2a-card.json`
- `marketplace/manifests/email-triage/SOUL.md`

## Verification

Green:

```bash
cd ~/Projects/agents
bash scripts/pf-qa.sh
```

Result:

- ruff: pass
- mypy: pass (`31 source files`)
- pytest: pass (`91 passed`, total coverage `81.83%`)
- bandit: pass
- pip-audit: pass, no known vulnerabilities; `pf-runtime` local package skipped because it is not on PyPI

Green:

```bash
cd ~/Projects/agents
PYTHONPATH=/Users/alexhale/Projects/agents/pf-runtime python3 tests/spec_self_consistency.py
python3 tests/profile_dir_contract.py
python3 tests/file_shape_classifier.py
python3 -m pytest tests/communications_marketplace_contract.py -q
```

Result:

- spec self-consistency: pass
- profile contract: 14 profiles pass
- file-shape classifier: 104 files scanned, 0 failures
- communications marketplace contract: 2 passed

## Important Implementation Notes

- V1 remains **read + propose only**. `assert_v1_action_allowed(..., applying=True)` raises `MutationNotAllowedError`.
- `ProposalStore` persists local proposed actions only. Approval marking exists, but provider apply workers do not exist yet.
- Provider helpers normalize payloads already fetched by clients. They do not call Gmail, Graph, or IMAP directly yet.
- The tool dispatcher intentionally implements only the schema subset needed by current PF Runtime tools to avoid adding a dependency. If future MCP tools need full Draft 2020-12, add `jsonschema` deliberately and update `SPEC.md`.
- `loop.py` recognizes only the narrow JSON tool-call envelope. Plain assistant text still works normally.
- Tool trace logs include argument hashes, never raw args.

## Next Steps for Claude

1. Review the communications slice only; avoid unrelated existing dirty files.
2. Decide whether to stage this as one atomic commit or split into:
   - `feat(pf-runtime): add communications proposal runtime`
   - `feat(marketplace): add communications-triage sku`
3. Before commit, rerun:
   - `bash scripts/pf-qa.sh`
   - `PYTHONPATH=/Users/alexhale/Projects/agents/pf-runtime python3 tests/spec_self_consistency.py`
   - `python3 tests/profile_dir_contract.py`
   - `python3 tests/file_shape_classifier.py`
   - `python3 -m pytest tests/communications_marketplace_contract.py -q`
4. Next implementation slice should be **connector credential/account registry plumbing**, not live writes:
   - load `account-registry.example.yaml`-shaped runtime config
   - add read-only Gmail client wrapper behind `normalize_gmail_message`
   - add read-only Graph client wrapper behind `normalize_graph_message`
   - add read-only IMAP fetch wrapper behind `normalize_imap_message`
   - emit PFOS `agent_events` for triage runs and proposal creation
5. Do not add these scopes in the next slice:
   - Gmail `gmail.modify`, `gmail.compose`, `gmail.send`, `mail.google.com`
   - Microsoft Graph `Mail.ReadWrite`, `Mail.Send`, `Calendars.ReadWrite`
   - SMTP send
   - Google Calendar write scopes

## Stop Conditions

- Any live mailbox/calendar mutation path appears before the approval/apply design is reviewed.
- Any connector requests a forbidden v1 write/send scope.
- `run_session` regresses existing Slack/CLI conversation behavior.
- PF Runtime QA or profile contract fails.

