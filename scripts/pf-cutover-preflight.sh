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

# ---------------------------------------------------------------------------
# Env vars required for communications-triage (Slice 4 PFOS emit).
# Source ~/.hermes/profiles/personal/.env if present — operator typically keeps
# tokens there. Missing PFOS event vars => emission silently no-ops; missing
# per-account creds => that account skips on triage.
# ---------------------------------------------------------------------------
PROFILE_ENV="$HOME/.hermes/profiles/personal/.env"
if [[ -f "$PROFILE_ENV" ]]; then
  echo ">> source $PROFILE_ENV (preflight only)"
  set -a
  # shellcheck disable=SC1090
  source "$PROFILE_ENV"
  set +a
else
  echo "info: $PROFILE_ENV not found — relying on inherited shell env"
fi

echo ">> PFOS event-emission env presence"
PFOS_MISSING=0
for var in PFOS_AGENT_EVENT_URL PFOS_AGENT_EVENT_TOKEN; do
  if [[ -z "${!var:-}" ]]; then
    echo "warn: $var not set — pf-runtime PFOS emit will no-op until configured" >&2
    PFOS_MISSING=$((PFOS_MISSING + 1))
  else
    echo "  $var: present"
  fi
done

REGISTRY="$HOME/.hermes/profiles/personal/account-registry.yaml"
if [[ -f "$REGISTRY" ]]; then
  echo ">> communications-triage account credential env presence (registry: $REGISTRY)"
  python3 - "$REGISTRY" <<'PY' || true
import os
import sys
import yaml

prefix = {
    "google_mail": "PF_GMAIL_TOKEN_",
    "google_calendar": "PF_GMAIL_TOKEN_",
    "microsoft_graph": "PF_GRAPH_TOKEN_",
    "imap_hostgator": "PF_IMAP_PASSWORD_",
}
data = yaml.safe_load(open(sys.argv[1], encoding="utf-8")) or {}
missing = []
for acct in data.get("accounts", []):
    aid = acct.get("account_id", "")
    pv = acct.get("provider", "")
    if not aid or pv not in prefix:
        continue
    env = prefix[pv] + aid.upper().replace("-", "_")
    if os.environ.get(env):
        print(f"  {env}: present ({pv} {aid})")
    else:
        print(f"warn: {env} missing ({pv} {aid})", file=sys.stderr)
        missing.append(env)
if missing:
    print(f"info: {len(missing)} account credential env var(s) missing — those accounts will skip on triage")
PY
else
  echo "info: $REGISTRY not found — communications-triage will load 0 accounts"
fi

echo ""
echo "Preflight OK. Next (operator):"
echo "  1) Foreground: cd $PF && python3 -m pf_runtime gateway --profile personal --hermes-home \"\$HOME/.hermes\""
echo "  2) Five DMs per CUTOVER_C_PLAYBOOK.md Step 5"
echo "  3) launchctl unload Hermes personal plist; promote .staged plist; launchctl load PF plist"
echo "  4) 50-DM / 24h Step 6 metrics"
