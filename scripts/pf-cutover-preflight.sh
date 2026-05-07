#!/usr/bin/env bash
# Preflight automation for Sub-phase C (CUTOVER_C_PLAYBOOK.md).
# Does NOT perform launchd swap or DM smoke — operator runs those after green exit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PF="$ROOT/pf-runtime"
STAGED_PLIST="$HOME/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist.staged"

echo "== PF Runtime cutover preflight (repo: $ROOT) =="

if [[ ! -d "$PF" ]]; then
  echo "error: pf-runtime not found at $PF" >&2
  exit 1
fi

cd "$PF"
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo ">> pf-qa (ruff, mypy, pytest+cov, bandit, pip-audit)"
bash "$ROOT/scripts/pf-qa.sh"

echo ">> launchd collision check (personal Hermes vs PF)"
if command -v launchctl >/dev/null 2>&1; then
  if launchctl list 2>/dev/null | grep -E 'ai\.hermes\.gateway-personal|ai\.prettyfly\.pf-runtime-personal' | wc -l | grep -q '^[[:space:]]*2$'; then
    echo "error: both Hermes personal gateway AND pf-runtime personal are loaded — unload one (see playbook Concurrent-Hermes)." >&2
    launchctl list 2>/dev/null | grep -E 'ai\.hermes\.gateway-personal|ai\.prettyfly\.pf-runtime-personal' || true
    exit 1
  fi
  launchctl list 2>/dev/null | grep -E 'ai\.hermes\.gateway-personal|ai\.prettyfly\.pf-runtime-personal' || echo "(no personal gateway job in launchctl list)"
else
  echo "(launchctl not available — skip collision check)"
fi

if [[ ! -f "$STAGED_PLIST" ]]; then
  echo "warn: staged plist missing: $STAGED_PLIST (create before cutover)" >&2
else
  echo ">> plutil -lint staged PF plist"
  plutil -lint "$STAGED_PLIST"
fi

echo ""
echo "Preflight OK. Next (operator):"
echo "  1) Foreground: cd $PF && python3 -m pf_runtime gateway --profile personal --hermes-home \"\$HOME/.hermes\""
echo "  2) Five DMs per CUTOVER_C_PLAYBOOK.md Step 5"
echo "  3) launchctl unload Hermes personal plist; promote .staged plist; launchctl load PF plist"
echo "  4) 50-DM / 24h Step 6 metrics"
