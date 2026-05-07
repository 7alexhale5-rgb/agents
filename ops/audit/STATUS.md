# Audit Tooling Status — 2026-05-07

Monorepo root [`package.json`](../../package.json) exists for `/audit-setup` (Node). Python / Hermes / `pf-runtime/` remain primary.

## Ran `/audit-setup` (full orchestrator)

| Tool                  | State     | Version   | Artifact                                                                                                                                        |
| --------------------- | --------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| Lighthouse            | ✓         | ^13.2.0   | [`ops/lighthouse/baseline/`](../lighthouse/baseline/) (`SUMMARY.md`, `*.report.json`), rerun [`run-baseline.sh`](../lighthouse/run-baseline.sh) |
| @axe-core/playwright  | ✓         | ^4.11     | [`tests/a11y/smoke.spec.ts`](../../tests/a11y/smoke.spec.ts)                                                                                    |
| @playwright/test      | ✓         | ^1.59     | [`playwright.config.ts`](../../playwright.config.ts) (webServer starts static `dist/`)                                                          |
| knip                  | ✓         | ^5        | [`knip.json`](../../knip.json) — root scripts + tests only (MCP subpackage analyzed separately)                                                 |
| Lighthouse CI         | ✓         | @lhci/cli | [`.github/workflows/lighthouse-ci.yml`](../../.github/workflows/lighthouse-ci.yml), [`.lighthouserc.json`](../../.lighthouserc.json)            |
| Bundle analyzer       | — skipped | —         | No Next.js/Vite root (skill default)                                                                                                            |
| @next/bundle-analyzer | N/A       | —         | Add when a web app ships in-tree                                                                                                                |

**Commands**

- A11y: `npm run build && npx playwright test --grep @a11y` (or rely on `webServer` in config)
- Dead code: `npm run dead-code`
- LH baseline: `npm run lh:baseline` or `bash ops/lighthouse/run-baseline.sh`
- LHCI local: `npm run lhci` (see [`.github/ci/README.md`](../../.github/ci/README.md))

Package manager: **npm**

## Python tier (`pf-runtime/`, `tests/`, `scripts/`)

| Tool               | State    | Notes                                                |
| ------------------ | -------- | ---------------------------------------------------- |
| ruff               | ✓        | `cd pf-runtime && ruff check pf_runtime tests`       |
| mypy               | ✓        | `cd pf-runtime && mypy pf_runtime`                   |
| pytest             | ✓        | `cd pf-runtime && pytest tests/`                     |
| bandit / pip-audit | periodic | See prior runs in git history; re-run after new deps |

## Nested Node (`mcp-servers/4d-senses/`)

Own [`package.json`](../../mcp-servers/4d-senses/package.json). Run `npm install && npm run smoke` there for MCP checks. Knip at repo root does not include that tree (avoid duplicate dependency resolution).

## What `/review-stack --audit` consumes

- This file — tooling baseline
- `ops/lighthouse/baseline/*.report.json` + `SUMMARY.md`
- `tests/a11y/smoke.spec.ts` + Playwright
- `knip.json` / `npx knip`
- Python gates above for `pf-runtime/` slices

## Next step

Run **`/review-stack --audit`** to apply Layer 4 against this tree.
