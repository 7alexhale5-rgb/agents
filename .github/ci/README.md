# Lighthouse CI

Scaffolded by [`/audit-setup`](https://github.com/anthropics/claude-code). Runs Lighthouse against every Vercel preview deploy, upserts a PR comment with score deltas vs the captured baseline.

The PR comment is posted by an `actions/github-script` step that reads `.lighthouseci/manifest.json` and upserts via a hidden marker (`<!-- lhci-scaffold:comment -->`) — no Lighthouse CI GitHub App installation required. Deltas are diffed against `ops/lighthouse/baseline/*.report.json`.

## Before you scaffold (run-once setup checklist)

- **Run `setup-ci.sh` from a clean checkout of your base branch (e.g. `main`)**, not from a feature branch. The scaffolder writes `.github/workflows/lighthouse-ci.yml`, `.lighthouserc.json`, `ops/lighthouse/baseline/*`, and modifies `package.json` + `package-lock.json`. If you scaffold from a feature branch, your throwaway PR diff will include unrelated work-in-progress and the cherry-pick onto a clean base will conflict on `package.json`.
- **Verify `git branch --show-current` matches expectation BEFORE the commit.** Pre-commit hooks (Husky, lint-staged) can stash + replay around the commit and have been observed landing the commit on a different branch than the one you started on. After `git commit`, run `git branch --show-current && git log -1 --oneline` to confirm placement.
- **If your repo's GitHub URL has a trailing punctuation character** (e.g. `YehovahBuilders/YEH.`), `gh pr create` may need explicit `--head` and `--base` flags — auto-detection sometimes fails on the repo-name parser.

## Default behavior: warn-only

On first install, every assertion defaults to `"warn"` level. Regressions show up in the PR comment but never fail the build. This lets you watch the numbers stabilize before gating merges.

## Flip to enforcing

Two paths:

**One-field edit** — open `.lighthouserc.json`. Each assertion is a `[level, options]` pair, e.g. `["warn", { "minScore": 0.84 }]`. Change `"warn"` to `"error"` for any assertion you want to gate on. Redeploy. Regressions now fail the workflow.

**Scripted** — `/audit-setup --ci-only --enforce` does the same thing and also bumps the sentinel version.

## Baseline refresh (after a legitimate improvement)

When a perf win bumps your scores above the captured baseline and you want the new numbers to become the reference:

```bash
npm run lh:bless
```

This reruns the baseline against production, regenerates `.lighthouserc.json` with the new numbers, and stages the changes. Review `git diff --staged`, then commit and open a PR.

## Uninstall

```bash
bash ~/.claude/skills/audit-setup/scripts/setup-ci.sh --uninstall
```

Removes this README, `.github/workflows/lighthouse-ci.yml`, `.github/ci/lh-bless.sh`, `.lighthouserc.json`, and the `lhci` / `lh:bless` scripts from `package.json`. Refuses if any of those files have been hand-edited (sentinel comment check).

## Files this workflow owns

| Path | Purpose |
|---|---|
| `.github/workflows/lighthouse-ci.yml` | Workflow definition (deployment_status trigger) |
| `.lighthouserc.json` | LHCI config + assertMatrix (warn-only by default) |
| `.github/ci/lh-bless.sh` | Baseline refresh script |
| `.github/ci/README.md` | This file |
| `ops/lighthouse/baseline/*.report.json` | Reference scores (owned by `/audit-setup --lighthouse-only`) |

## Vercel Deployment Protection (preview SSO)

The workflow's `Verify preview is publicly accessible` step pre-flights the preview URL with `curl`. If it returns HTTP 401 or 403, the workflow fails fast (~21s) with a clear error.

This guards against a silent false-pass: when Vercel Deployment Protection is on, Lighthouse follows the redirect to `vercel.com/login` and audits the login page. Login-page paths don't match any `assertMatrix` pattern (`.*/press$`, etc.), so **all assertions silently skip and the run reports success — including `level: "error"` ones**.

If you see this guard fail, two unblock paths:

1. **Disable Vercel Deployment Protection on Preview deploys** — Vercel dashboard → Settings → Deployment Protection → set Preview to "None" or "Bypass URLs only". Easiest; loses preview-link privacy.
2. **Add a Protection Bypass for Automation token** — Vercel dashboard → Settings → Deployment Protection → Protection Bypass for Automation → Generate Secret. Add as `VERCEL_AUTOMATION_BYPASS_SECRET` repo secret. Modify the workflow's `Build route list from baseline` step to append `?x-vercel-protection-bypass=$SECRET` to each URL (or pass via `x-vercel-protection-bypass` HTTP header in a custom Lighthouse runner config).

## Off-ramp: trended history across PRs

This setup uses LHCI's `temporary-public-storage` (artifacts expire in ~7 days). If you ever need trended scores across every PR:

1. Stand up an LHCI server (Heroku / fly.io / Cloudflare Workers).
2. Add `LHCI_GITHUB_APP_TOKEN` secret.
3. Change the `Run Lighthouse CI` step's `target` to `lhci` and set `serverBaseUrl`.

No other file changes needed. The github-script PR comment continues working alongside.

## Limitations

- `deployment_status` events don't fire for PRs from forks. External contributor PRs won't get a Lighthouse comment.
- Preset (mobile vs desktop) must match the captured baseline. If you change the preset in `.lighthouserc.json`, regenerate the baseline via `/audit-setup --lighthouse-only --force`.
- Lighthouse scores on GitHub-hosted runners (2-core) are systematically lower than on local development machines or Vercel CDN. If your baseline was captured locally, expect persistent ~30-50 point delta in `performance` regardless of code changes. Capture baseline against the same surface you'll audit (e.g. production CDN) to keep deltas meaningful.
