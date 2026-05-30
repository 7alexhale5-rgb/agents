#!/usr/bin/env bash
# scout-eval.sh — rapid, on-demand eval of a Research Scout Fleet scout.
#
# Two loops (see ~/.claude/plans/build-the-research-scout-soft-lightning.md):
#   * RAPID (default): fixture-driven promptfoo run. No live network, no
#     /research-stack, no NotebookLM. Fixtures stand in for the swept-sources
#     block; the prompt is assembled from the scout's live SOUL/DOCTRINE/
#     topic-sweep by _shared/scout-eval/build-prompt.mjs. This is the
#     prompt-refinement engine — run it hundreds of times cheaply.
#   * LIVE (--live): one real sweep via fleet-invoke.sh, gated to 2/day/scout
#     (fleet/limits.json). Validates the end-to-end path; NOT the rapid loop.
#
# Usage:
#   scripts/scout-eval.sh <scout> [--runs N] [--smoke] [--json] [--live]
#
#   <scout>     hermes-scout | cc-scout | mcp-scout | pkm-scout
#   --runs N    promptfoo --repeat count (default 1). The "hundreds of times" knob.
#   --smoke     include the free nemotron model as an under-test provider
#               (cheap variance probing; excluded from the gate either way).
#   --json      print the machine-readable gate summary (for the Workflow fan-out).
#   --live      run a real sweep via fleet-invoke.sh instead of the rapid loop.
#
# Examples:
#   scripts/scout-eval.sh hermes-scout --runs 10
#   scripts/scout-eval.sh cc-scout --runs 50 --smoke --json
#   scripts/scout-eval.sh mcp-scout --live

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILES_DIR="$REPO_ROOT/hermes/profiles"
RUNS_DIR="$REPO_ROOT/.runs/scout-eval"
LIMITS_JSON="$REPO_ROOT/fleet/limits.json"
LIVE_COUNTS="$REPO_ROOT/fleet/.scout-eval-live-counts.json"
SUMMARY="$REPO_ROOT/scripts/scout-eval-summary.py"

SCOUT="${1:-}"
shift || true

RUNS=1
SMOKE=""
JSON=""
LIVE=""
ANTHROPIC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --runs) RUNS="$2"; shift 2 ;;
    --smoke) SMOKE=1; shift ;;
    --json) JSON=1; shift ;;
    --live) LIVE=1; shift ;;
    --anthropic) ANTHROPIC=1; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

case "$SCOUT" in
  hermes-scout|cc-scout|mcp-scout|pkm-scout) ;;
  *) echo "Usage: $0 <hermes-scout|cc-scout|mcp-scout|pkm-scout> [--runs N] [--smoke] [--json] [--live] [--anthropic]" >&2; exit 2 ;;
esac

CONFIG="$PROFILES_DIR/$SCOUT/eval/promptfoo.yaml"
[ -f "$CONFIG" ] || { echo "error: no promptfoo config at $CONFIG" >&2; exit 2; }

# load_key NAME — read an API key value from the hermes runtime env files.
load_key() {
  local name="$1"
  local cur; cur="$(printenv "$name" || true)"
  [ -n "$cur" ] && { printf '%s' "$cur"; return; }
  for envf in "$HOME/.hermes/litellm/.env" "$HOME/.hermes/.env"; do
    [ -f "$envf" ] || continue
    local v; v="$(python3 - "$envf" "$name" <<'PY'
import sys
name = sys.argv[2]
for line in open(sys.argv[1], encoding="utf-8"):
    line = line.strip()
    if line.startswith("#") or not line.startswith(name + "="):
        continue
    val = line.split("=", 1)[1].strip().strip('"').strip("'")
    if val:
        print(val)
    break
PY
)"
    [ -n "$v" ] && { printf '%s' "$v"; return; }
  done
}

# Provider path. Default: OpenRouter (the scouts' real runtime provider).
# --anthropic: Anthropic-direct on the same Sonnet/Haiku models (fallback when
# OpenRouter credits are dry); a swapped config is generated in eval/.
CONFIG_RUN="$CONFIG"
if [ -n "$ANTHROPIC" ]; then
  ANTHROPIC_API_KEY="$(load_key ANTHROPIC_API_KEY)"; export ANTHROPIC_API_KEY
  [ -n "${ANTHROPIC_API_KEY:-}" ] || { echo "error: ANTHROPIC_API_KEY not found (checked env, ~/.hermes/litellm/.env)" >&2; exit 2; }
  CONFIG_RUN="$PROFILES_DIR/$SCOUT/eval/.promptfoo.anthropic.yaml"
  # Swap OpenRouter provider + grader ids to Anthropic-direct equivalents.
  # nemotron stays in the file but is filtered out below unless --smoke.
  sed -e 's#openrouter:anthropic/claude-sonnet-4.6#anthropic:claude-sonnet-4-6#g' \
      -e 's#openrouter:anthropic/claude-haiku-4.5#anthropic:claude-haiku-4-5#g' \
      "$CONFIG" > "$CONFIG_RUN"
else
  OPENROUTER_API_KEY="$(load_key OPENROUTER_API_KEY)"; export OPENROUTER_API_KEY
  [ -n "${OPENROUTER_API_KEY:-}" ] || { echo "error: OPENROUTER_API_KEY not found (checked env, ~/.hermes/litellm/.env, ~/.hermes/.env)" >&2; exit 2; }
fi

# ---------------------------------------------------------------------------
# LIVE loop — gated to limits.json (2/day/scout). Not the rapid loop.
# ---------------------------------------------------------------------------
if [ -n "$LIVE" ]; then
  CAP="$(python3 -c "import json,sys; print(json.load(open('$LIMITS_JSON')).get('limits',{}).get('$SCOUT',0))" 2>/dev/null || echo 0)"
  TODAY="$(date -u +%Y-%m-%d)"
  USED="$(python3 -c "import json,os; p='$LIVE_COUNTS'; d=json.load(open(p)) if os.path.exists(p) else {}; print(d.get('$TODAY',{}).get('$SCOUT',0))" 2>/dev/null || echo 0)"
  if [ "$CAP" -gt 0 ] && [ "$USED" -ge "$CAP" ]; then
    echo "live cap reached for $SCOUT: $USED/$CAP today ($TODAY). Rapid loop is uncapped — drop --live." >&2
    exit 3
  fi
  python3 - "$LIVE_COUNTS" "$TODAY" "$SCOUT" <<'PY'
import json, os, sys
path, today, scout = sys.argv[1:4]
d = json.load(open(path)) if os.path.exists(path) else {}
d.setdefault(today, {}); d[today][scout] = d[today].get(scout, 0) + 1
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump(d, open(path, "w"), indent=2)
PY
  echo "live sweep: $SCOUT topic-sweep (used $((USED+1))/$CAP today)"
  exec bash "$REPO_ROOT/scripts/fleet-invoke.sh" "$SCOUT" topic-sweep
fi

# ---------------------------------------------------------------------------
# RAPID loop — fixture-driven promptfoo. --no-cache so --repeat measures real
# run-to-run variance instead of returning cached identical outputs.
# ---------------------------------------------------------------------------
mkdir -p "$RUNS_DIR"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$RUNS_DIR/${SCOUT}-${TS}.json"

PF_ARGS=(eval -c "$CONFIG_RUN" --repeat "$RUNS" --no-cache --output "$OUT")
if [ -z "$SMOKE" ]; then
  # Drop the free smoke model from the under-test set unless --smoke.
  PF_ARGS+=(--filter-providers '^(?!.*nemotron).*$')
fi

# In --json mode keep stdout clean for machine consumers (the Workflow fan-out):
# promptfoo's table goes to stderr, only the summary JSON lands on stdout.
if [ -n "$JSON" ]; then
  echo "scout-eval: $SCOUT  runs=$RUNS  smoke=${SMOKE:-0}  → $OUT" >&2
  ( cd "$REPO_ROOT" && promptfoo "${PF_ARGS[@]}" --no-progress-bar ) >&2 2>&1 || true
else
  echo "scout-eval: $SCOUT  runs=$RUNS  smoke=${SMOKE:-0}  → $OUT"
  ( cd "$REPO_ROOT" && promptfoo "${PF_ARGS[@]}" ) || true
fi

# Summary + gate (Phase 3 script). Falls back to promptfoo's native table if absent.
if [ -f "$SUMMARY" ]; then
  if [ -n "$JSON" ]; then
    python3 "$SUMMARY" "$OUT" --json
  else
    python3 "$SUMMARY" "$OUT"
  fi
else
  echo "(scout-eval-summary.py not present yet — see promptfoo table above; raw JSON at $OUT)"
fi
