#!/bin/bash
# audit-setup:lh-bless v1 — scripted baseline refresh
#
# Reruns the Lighthouse baseline against production, then regenerates
# .lighthouserc.json assertions from the new numbers. Never commits — leaves
# changes staged so you can review the diff before opening a PR.
#
# Usage: bash .github/ci/lh-bless.sh
#
# Prerequisite: ops/lighthouse/run-baseline.sh must be env-aware (supports
# LH_TARGET_URL / LH_ROUTES / LH_RUNS). If yours is a legacy hand-written
# version, regenerate via: /audit-setup --lighthouse-only --force

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$PROJECT_DIR"

echo "=== lh-bless: rerunning baseline against production ==="
if [[ ! -x ops/lighthouse/run-baseline.sh ]]; then
  echo "!!! ops/lighthouse/run-baseline.sh missing or not executable"
  echo "    Run: /audit-setup --lighthouse-only --force"
  exit 1
fi

# Detect legacy (non-env-aware) rerun script. Legacy versions don't read
# LH_TARGET_URL; they hardcode the URL. Abort loudly.
if ! grep -q 'LH_TARGET_URL' ops/lighthouse/run-baseline.sh; then
  echo "!!! ops/lighthouse/run-baseline.sh is legacy (no env-var support)"
  echo "    Run: /audit-setup --lighthouse-only --force"
  exit 1
fi

# User can override via env; otherwise use the URL the script was seeded with.
bash ops/lighthouse/run-baseline.sh

echo ""
echo "=== lh-bless: regenerating .lighthouserc.json from new baseline ==="
if command -v claude-skill >/dev/null 2>&1; then
  # Future: when audit-setup ships a CLI wrapper, use it.
  claude-skill audit-setup --ci-only --regen-assertions-only --project-dir "$PROJECT_DIR"
else
  # Today: call setup-ci.sh directly from the user's ~/.claude install.
  SKILL_CI="$HOME/.claude/skills/audit-setup/scripts/setup-ci.sh"
  if [[ ! -x "$SKILL_CI" ]]; then
    echo "!!! $SKILL_CI missing or not executable"
    echo "    audit-setup skill not installed or out of date"
    exit 1
  fi
  bash "$SKILL_CI" --project-dir "$PROJECT_DIR" --regen-assertions-only
fi

echo ""
echo "=== lh-bless: staging changes ==="
git add ops/lighthouse/baseline/ .lighthouserc.json 2>/dev/null || true

echo ""
echo "=== Done ==="
echo "Review the diff: git diff --staged"
echo "Commit + PR when ready: git commit -m 'chore: refresh Lighthouse baseline' && gh pr create"
