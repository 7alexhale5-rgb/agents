# Audit Tooling Status — 2026-05-06

> Bootstrap baseline for Phase 4.7 PrettyFly Runtime pre-work. Web-tier audits (Lighthouse / axe / bundle / knip) **N/A** — `~/Projects/agents/` has no Next.js root, only manifest catalogs and a Node MCP server (`mcp-servers/4d-senses/`). Python tooling per LAIK convention.

## Python tier (pf-runtime/ + tests/ + scripts/)

| Tool      | State        | Version | Result                                                                                                                                                                             |
| --------- | ------------ | ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ruff      | ✅ installed | 0.14.5  | **PASS** — 0 errors after `--fix` (4 auto-fixed: unused imports)                                                                                                                   |
| mypy      | ✅ installed | 1.18.2  | **PASS** — strict mode, 6 source files, 0 issues                                                                                                                                   |
| bandit    | ✅ installed | 1.8.6   | **3 Medium / 7 Low** — all in pre-existing scripts (`honcho-publish-eval-trace.py`, `honcho-substrate-bootstrap.py`, `vanclief-eval-summary.py`); none in Phase 4.7 pre-work files |
| pip-audit | ✅ installed | 2.9.0   | Deferred until first dep install (`pip install -e pf-runtime/[runtime,channels,dev]`) — no production deps yet at v0.1-pre                                                         |
| pytest    | ✅ available | 8.x     | **1 PASS** (`tests/spec_self_consistency.py` — 4 contracts verified)                                                                                                               |

## Node tier (mcp-servers/4d-senses/)

| Tool                | State    | Notes                                                                          |
| ------------------- | -------- | ------------------------------------------------------------------------------ |
| Lighthouse          | N/A      | No Next.js / Vite / Astro root                                                 |
| axe-core/playwright | N/A      | No Playwright; non-UI server                                                   |
| bundle analyzer     | N/A      | No frontend                                                                    |
| knip                | Deferred | TS dead-code detection valuable later if 4d-senses grows; not gating Phase 4.7 |

## Pre-existing finding inventory (carry-forward)

These bandit Medium findings exist in scripts that pre-date Phase 4.7. They are **not gating** Phase 4.7 — listed for follow-up:

| File                                    | Line | CWE    | Issue                                   |
| --------------------------------------- | ---- | ------ | --------------------------------------- |
| `scripts/honcho-publish-eval-trace.py`  | 65   | CWE-22 | `urllib.urlopen` without URL validation |
| `scripts/honcho-substrate-bootstrap.py` | 70   | CWE-22 | `urllib.urlopen` without URL validation |
| `scripts/vanclief-eval-summary.py`      | 58   | CWE-22 | `urllib.urlopen` without URL validation |

Action: in a follow-up sweep, swap to `httpx` with explicit URL allowlist OR add `# nosec B310` comments with rationale. Not a Phase 4.7 blocker.

## Coverage

Phase 4.7 pre-work (4 design docs + 3 scripts + stubs + 1 test):

```
pf-runtime/
├── pf_runtime/__init__.py        ruff ✅  mypy ✅
├── pf_runtime/stubs/__init__.py  ruff ✅  mypy ✅
├── pf_runtime/stubs/spec_stubs.py ruff ✅  mypy ✅
├── pyproject.toml                (config; not lint target)
├── SPEC.md                       (markdown; review by Codex)
├── docs/MEMORY_LIFECYCLE.md      (markdown; review by Codex)
├── docs/SKILL_SELF_GEN_BOUNDS.md (markdown; review by Codex)
└── docs/ADAPTER_PLUGIN_INTERFACE.md (markdown; review by Codex)

tests/
├── __init__.py                   ruff ✅  mypy ✅
├── profile_dir_contract.py       ruff ✅  mypy ✅  PASS (13/13 profiles)
└── spec_self_consistency.py      ruff ✅  mypy ✅  PASS (4/4 contracts)

scripts/
├── hermes-commit-watcher.sh      bash; shellcheck not yet wired
└── hermes-feature-audit.sh       bash; shellcheck not yet wired
```

## What `/review-stack --deep --audit` will consume

- This file (`ops/audit/STATUS.md`) for tooling baseline
- ruff + mypy + bandit results above
- `tests/profile_dir_contract.py` already runs nightly via launchd (Phase 4.7 pre-work item B)
- `tests/spec_self_consistency.py` runs once-per-CI for SPEC.md drift detection
- The Codex review handoff at `.planning/handoff-codex.md` for cross-tool diff review

## Next sweep

- Wire shellcheck into pre-commit for `scripts/*.sh` (low priority — small attack surface)
- After sub-phase 4.7.1 lands real `runtime/loop.py`: re-run full audit + capture diff
- pip-audit fires once `pip install -e pf-runtime/[runtime,channels]` (post-greenlight)
