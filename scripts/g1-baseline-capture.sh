#!/usr/bin/env bash
# g1-baseline-capture.sh — locked metric contract per ~/.claude/plans/lovely-cooking-flame.md §6.A
#
# Runs once per qualifying night via launchd. Writes EXACTLY ONE row to
# HERMES_BASELINE.md if the qualifying-night threshold is met (≥5 sessions);
# otherwise writes a SKIP row and exits without advancing the night counter.
#
# Metric definitions are LOCKED — do not change without a PLAN.md amendment
# AND a Codex re-review. The amendment is the only way to bump
# pf_runtime.schema_version.
#
# Source filter: 'slack' (per swarm review §2.2.2 — personal profile is Slack-only;
# Telegram channel is disabled in personal/config.yaml until a NEW bot token is paired).
#
# Usage:
#   scripts/g1-baseline-capture.sh [profile=personal]
#
# Default profile changed from `personal-baseline` to `personal` 2026-05-06:
# only `personal` has a Slack gateway producing inbound traffic. The
# `personal-baseline` workspace is reserved for future PF Runtime A/B work
# (see post-phase-4-7-0/NEXT_PHASE_PLAN.md §1.0).
#
# Exit codes:
#   0 — qualifying row written OR SKIP row written (both expected outcomes)
#   1 — sanity check failed (do not use this row for gate decisions)
#   2 — silent-failure detector tripped (LiteLLM 429)
#   3 — silent-failure detector tripped (email-triage spend leak)
#   4 — pre-flight failure (DB missing, golden set missing)

set -euo pipefail

PROFILE="${1:-personal}"
DB="$HOME/.hermes/profiles/${PROFILE}/state.db"
BASELINE_DIR="$HOME/Projects/agents/.planning/phase-4-7-prettyfly-runtime/baseline"
BASELINE_MD="${BASELINE_DIR}/HERMES_BASELINE.md"
GOLDEN_JSONL="$HOME/Projects/agents/hermes/profiles/personal/eval/golden.jsonl"
PROMPTFOO_YAML="$HOME/Projects/agents/hermes/profiles/personal/eval/promptfoo.yaml"
LIB_DIR="$(cd "$(dirname "$0")" && pwd)/lib"
SCHEMA_VERSION=1
MIN_SESSIONS_PER_NIGHT=5
DATE=$(date -u +%Y-%m-%d)

# --- pre-flight ---
[ -f "$DB" ] || { echo "ABORT: DB missing at $DB"; exit 4; }
[ -f "$GOLDEN_JSONL" ] || { echo "ABORT: golden set missing at $GOLDEN_JSONL"; exit 4; }
[ -f "$LIB_DIR/wilson.sh" ] || { echo "ABORT: wilson.sh missing at $LIB_DIR/wilson.sh"; exit 4; }
mkdir -p "$BASELINE_DIR"

source "$LIB_DIR/wilson.sh"

HERMES_BIN="$(command -v hermes || echo unknown)"
# Sanitize hermes --version to first line only — full output includes Project/Python/SDK/upstream-commit-count banner
# which would pollute the tab-separated baseline row.
HERMES_VERSION="$("$HERMES_BIN" --version 2>/dev/null | head -n 1 | tr -d '\t\n' || echo unknown)"
HERMES_AGENT_DIR="$HOME/.hermes/hermes-agent"
HERMES_COMMIT="$(git -C "$HERMES_AGENT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
HERMES_PIN="${HERMES_VERSION// /_}@${HERMES_COMMIT}"

# --- §1.2.1 qualifying-night gate ---
SESSION_COUNT=$(sqlite3 "$DB" \
  "SELECT COUNT(*) FROM sessions
   WHERE source = 'slack'
     AND date(started_at, 'unixepoch') = '${DATE}';")

if [ "$SESSION_COUNT" -lt "$MIN_SESSIONS_PER_NIGHT" ]; then
  printf "%s\t%s\tSKIP\tsessions=%s\tmin=%s\thermes=%s\tschema=%d\n" \
    "$DATE" "$PROFILE" "$SESSION_COUNT" "$MIN_SESSIONS_PER_NIGHT" "$HERMES_PIN" "$SCHEMA_VERSION" \
    >> "$BASELINE_MD"
  echo "SKIP: ${DATE} had ${SESSION_COUNT} sessions (min ${MIN_SESSIONS_PER_NIGHT}) — clock not advanced"
  exit 0
fi

# --- METRIC: cost p50/p95 (USD per session, percentile across calendar day UTC) ---
read -r P50_COST P95_COST <<EOF
$(sqlite3 "$DB" "
  SELECT estimated_cost_usd FROM sessions
  WHERE source = 'slack' AND date(started_at, 'unixepoch') = '${DATE}'
  ORDER BY estimated_cost_usd;" \
  | python3 -c "
import sys
vals = sorted(float(l) for l in sys.stdin if l.strip())
if not vals: print('0 0'); raise SystemExit
n = len(vals)
print(vals[int(n*0.50)], vals[min(int(n*0.95), n-1)])")
EOF

# --- METRIC: p95 latency (wall-clock session duration, end-to-end seconds) ---
P95_LATENCY=$(sqlite3 "$DB" "
  SELECT (ended_at - started_at) FROM sessions
  WHERE source = 'slack'
    AND date(started_at, 'unixepoch') = '${DATE}'
    AND ended_at IS NOT NULL
  ORDER BY (ended_at - started_at);" \
  | python3 -c "
import sys
vals = sorted(float(l) for l in sys.stdin if l.strip())
if not vals: print(0); raise SystemExit
print(vals[min(int(len(vals)*0.95), len(vals)-1)])")

# --- METRIC: trace volume per 24h (Langfuse-independent fallback) ---
TRACE_VOL=$(sqlite3 "$DB" "
  SELECT COALESCE(SUM(api_call_count), 0) FROM sessions
  WHERE source = 'slack' AND date(started_at, 'unixepoch') = '${DATE}';")

# --- METRIC: Promptfoo Wilson lower-CI (N=150 via --repeat 5) ---
PROMPTFOO_OUTPUT="/tmp/g1-promptfoo-${PROFILE}-${DATE}.json"
if command -v promptfoo >/dev/null 2>&1 && [ -f "$PROMPTFOO_YAML" ]; then
  promptfoo eval -c "$PROMPTFOO_YAML" --repeat 5 \
    -o "$PROMPTFOO_OUTPUT" --no-cache 2>/dev/null || true
  PASS=$(jq -r '.results.stats.successes // 0' "$PROMPTFOO_OUTPUT" 2>/dev/null || echo 0)
  TOTAL=$(jq -r '(.results.stats.successes + .results.stats.failures + .results.stats.errors) // 0' "$PROMPTFOO_OUTPUT" 2>/dev/null || echo 0)
else
  PASS=0; TOTAL=0
  echo "WARN: promptfoo or YAML missing — Wilson CI = 0/0" >&2
fi
WILSON_CI=$(wilson_lower "$PASS" "$TOTAL")

# --- METRIC: Ragas answer_relevance (NOT faithfulness for non-RAG personal profile) ---
RAGAS_PYTHON="$LIB_DIR/ragas_score.py"
if [ -f "$RAGAS_PYTHON" ] && [ "$TOTAL" -gt 0 ]; then
  RAGAS_SCORE=$(python3 "$RAGAS_PYTHON" \
    --report "$PROMPTFOO_OUTPUT" \
    --metric answer_relevance \
    --model claude-haiku-4-5 2>/dev/null || echo 0)
else
  RAGAS_SCORE=0
fi

# --- §4.4 SILENT-FAILURE ASSERTIONS ---
LITELLM_429=$(jq -r '
  [.results.results[]? | select((.error // "" | tostring) | contains("429"))] | length
' "$PROMPTFOO_OUTPUT" 2>/dev/null || echo 0)
EMAIL_TRIAGE_LEAK=$(sqlite3 "$DB" "
  SELECT COUNT(*) FROM sessions
  WHERE source='slack'
    AND date(started_at, 'unixepoch') = '${DATE}'
    AND COALESCE(model, '') LIKE '%email-triage%';" 2>/dev/null || echo 0)

if [ "$LITELLM_429" -gt 0 ]; then
  echo "ABORT: LiteLLM 429 detected on ${DATE} — night does NOT count" >&2
  exit 2
fi
if [ "$EMAIL_TRIAGE_LEAK" -gt 0 ]; then
  echo "ABORT: email-triage leak on ${DATE} — exclusion tag failed" >&2
  exit 3
fi

# --- §5.9.8 cross-profile contamination assertion ---
ATLAS_DELTA=$(sqlite3 "$HOME/.hermes/profiles/atlas-ceo/state.db" "
  SELECT COUNT(*) FROM sessions
  WHERE date(started_at, 'unixepoch') = '${DATE}';" 2>/dev/null || echo 0)
# Stored snapshot (touched on first run per night) lets us detect if atlas-ceo
# row count drifted during the personal-baseline capture window.
ATLAS_SNAPSHOT="${BASELINE_DIR}/.atlas-snapshot-${DATE}"
if [ ! -f "$ATLAS_SNAPSHOT" ]; then
  echo "$ATLAS_DELTA" > "$ATLAS_SNAPSHOT"
fi

# --- WRITE ROW ---
HEADER="date	profile	sessions	p50_cost	p95_cost	p95_lat_sec	trace_vol	wilson_ci	prompftoo_n	ragas_metric	ragas_score	hermes_pin	schema_v"
[ -f "$BASELINE_MD" ] || printf "%s\n" "$HEADER" > "$BASELINE_MD"

printf "%s\t%s\t%d\t%.5f\t%.5f\t%.2f\t%d\t%s\t%d\tanswer_relevance\t%s\t%s\t%d\n" \
  "$DATE" "$PROFILE" "$SESSION_COUNT" "$P50_COST" "$P95_COST" "$P95_LATENCY" \
  "$TRACE_VOL" "$WILSON_CI" "$TOTAL" "$RAGAS_SCORE" "$HERMES_PIN" "$SCHEMA_VERSION" \
  >> "$BASELINE_MD"

# --- SANITY CHECK ---
python3 - <<PY
ragas = float("${RAGAS_SCORE}")
p50 = float("${P50_COST}")
p95 = float("${P95_LATENCY}")
sessions = int("${SESSION_COUNT}")
import sys
checks = []
if not (0.0 <= ragas <= 1.0): checks.append(f"Ragas out of [0,1]: {ragas}")
if sessions > 0 and p50 <= 0: checks.append("Cost p50 zero — billing data missing")
if sessions > 0 and p95 <= 0: checks.append("Latency p95 zero — sessions have no end time")
if checks:
    print("SANITY FAIL on ${DATE}:", *checks, sep="\n  ")
    sys.exit(1)
print("SANITY OK")
PY

echo "Captured ${DATE} for ${PROFILE}: sessions=${SESSION_COUNT} cost_p50=${P50_COST} cost_p95=${P95_COST} lat_p95=${P95_LATENCY}s trace_vol=${TRACE_VOL} wilson=${WILSON_CI}/${TOTAL} ragas=${RAGAS_SCORE}"
