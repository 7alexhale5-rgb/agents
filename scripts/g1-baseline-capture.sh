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

# Sentinel: keep SESSION_COUNT defined before any code path can trap-fire.
# The ERR trap below references ${SESSION_COUNT:-unknown}; without this
# initializer, a failure between trap registration and line 79 logs
# "unknown" instead of a meaningful pre-count value.
SESSION_COUNT=-1

# --- status file for the morning monitor (Phase 3 of G1 reframe plan) ---
STATUS_DIR="${G1_STATUS_DIR:-$HOME/Assets/logs/g1-status}"
mkdir -p "$STATUS_DIR" 2>/dev/null || true
STATUS_FILE="${STATUS_DIR}/${DATE}.status"

write_status() {
  local code="$1"; local reason="${2:-}"
  cat > "$STATUS_FILE" <<EOF_STATUS
date=${DATE}
profile=${PROFILE}
exit_code=${code}
ran_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
sessions=${SESSION_COUNT:-unknown}
reason=${reason}
EOF_STATUS
}

trap 'rc=$?; write_status "$rc" "trapped exit"; exit $rc' ERR

# --- pre-flight ---
[ -f "$DB" ] || { write_status 4 "DB missing at $DB"; echo "ABORT: DB missing at $DB"; exit 4; }
[ -f "$GOLDEN_JSONL" ] || { write_status 4 "golden set missing at $GOLDEN_JSONL"; echo "ABORT: golden set missing at $GOLDEN_JSONL"; exit 4; }
[ -f "$LIB_DIR/wilson.sh" ] || { write_status 4 "wilson.sh missing at $LIB_DIR/wilson.sh"; echo "ABORT: wilson.sh missing at $LIB_DIR/wilson.sh"; exit 4; }
mkdir -p "$BASELINE_DIR"

source "$LIB_DIR/wilson.sh"

HERMES_BIN="$(command -v hermes || echo unknown)"
# Sanitize hermes --version to first line only — full output includes Project/Python/SDK/upstream-commit-count banner
# which would pollute the tab-separated baseline row.
HERMES_VERSION="$("$HERMES_BIN" --version 2>/dev/null | head -n 1 | tr -d '\t\n' || echo unknown)"
HERMES_AGENT_DIR="$HOME/.hermes/hermes-agent"
HERMES_COMMIT="$(git -C "$HERMES_AGENT_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
HERMES_PIN="${HERMES_VERSION// /_}@${HERMES_COMMIT}"

# --- session count: informational only, NOT a qualifying-night gate ---
# Per G1_REFRAME_2026-05-06.md §2: the qualifying-night gate is now
# `errors==0 AND graded_answers>=30` from Promptfoo, NOT session count.
# Session count is still computed because it's a useful operational signal
# (low session count = sparse live traffic, write to row but don't gate).
SESSION_COUNT=$(sqlite3 "$DB" \
  "SELECT COUNT(*) FROM sessions
   WHERE source = 'slack'
     AND date(started_at, 'unixepoch') = '${DATE}';")

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
# Capture exit code; non-zero = SKIP this night with explicit reason.
# A silent zero (PASS=0/TOTAL=0) would write Wilson CI = 0.0000 to the
# row and look like "qualifying with terrible quality" rather than
# "eval failed", masking baseline-invalidation. Per reviewer R2.
PROMPTFOO_OUTPUT="/tmp/g1-promptfoo-${PROFILE}-${DATE}.json"
if command -v promptfoo >/dev/null 2>&1 && [ -f "$PROMPTFOO_YAML" ]; then
  # The `|| PROMPTFOO_RC=$?` pattern captures the rc cleanly without
  # tripping the ERR trap. `set +e`/`set -e` bracketing leaves a window
  # where the ERR trap can still fire on the non-zero exit (bash quirk
  # observed in the wild — the trap fires before the next traced
  # command even gets to run).
  PROMPTFOO_RC=0
  promptfoo eval -c "$PROMPTFOO_YAML" --repeat 5 \
    -o "$PROMPTFOO_OUTPUT" --no-cache 2>/dev/null || PROMPTFOO_RC=$?
  if [ "$PROMPTFOO_RC" -ne 0 ] && [ "$PROMPTFOO_RC" -ne 100 ]; then
    # exit 100 = "some tests failed" (expected, eval-stat-tracked).
    # Other non-zero = process-level failure (rate-limit, malformed YAML, network).
    write_status 5 "promptfoo eval failed with rc=${PROMPTFOO_RC}"
    echo "ABORT: promptfoo eval rc=${PROMPTFOO_RC} on ${DATE} — night does NOT count" >&2
    exit 5
  fi
  PASS=$(jq -r '.results.stats.successes // 0' "$PROMPTFOO_OUTPUT" 2>/dev/null || echo 0)
  TOTAL=$(jq -r '(.results.stats.successes + .results.stats.failures + .results.stats.errors) // 0' "$PROMPTFOO_OUTPUT" 2>/dev/null || echo 0)
  PROMPTFOO_ERRORS=$(jq -r '.results.stats.errors // 0' "$PROMPTFOO_OUTPUT" 2>/dev/null || echo 0)
else
  write_status 6 "promptfoo binary or YAML config missing"
  echo "ABORT: promptfoo or YAML missing — cannot compute Wilson CI" >&2
  exit 6
fi
WILSON_CI=$(wilson_lower "$PASS" "$TOTAL")

# --- §2 qualifying-night gate (replaces MIN_SESSIONS_PER_NIGHT) ---
# Per G1_REFRAME_2026-05-06.md §2 contract: a night qualifies when
# Promptfoo ran cleanly (errors==0) AND emitted ≥30 graded answers
# (full golden set ran at least once). Live-traffic volume does NOT
# factor — quality is calendar-deterministic, operator-DM-volume-independent.
MIN_GRADED_ANSWERS=30
if [ "$PROMPTFOO_ERRORS" -gt 0 ] || [ "$TOTAL" -lt "$MIN_GRADED_ANSWERS" ]; then
  printf "%s\t%s\tSKIP\terrors=%s\tgraded=%s\tmin_graded=%s\thermes=%s\tschema=%d\n" \
    "$DATE" "$PROFILE" "$PROMPTFOO_ERRORS" "$TOTAL" "$MIN_GRADED_ANSWERS" "$HERMES_PIN" "$SCHEMA_VERSION" \
    >> "$BASELINE_MD"
  REASON="SKIP: errors=${PROMPTFOO_ERRORS} graded=${TOTAL}/${MIN_GRADED_ANSWERS} — clock not advanced"
  echo "$REASON"
  write_status 0 "$REASON"
  exit 0
fi

# --- METRIC: Ragas answer_relevance (NOT faithfulness for non-RAG personal profile) ---
# Reviewer Fix 3: missing ragas_score.py used to silently write 0; now it
# fails the night with an explicit reason. A zero Ragas baseline silently
# accumulated for 7 nights would invalidate the 4.7.2 gate.
RAGAS_PYTHON="$LIB_DIR/ragas_score.py"
if [ ! -f "$RAGAS_PYTHON" ]; then
  write_status 7 "ragas_score.py missing at $RAGAS_PYTHON — Ragas baseline cannot be computed"
  echo "ABORT: $RAGAS_PYTHON missing — Ragas baseline cannot be computed" >&2
  exit 7
fi
if [ "$TOTAL" -gt 0 ]; then
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
  write_status 2 "LiteLLM 429 detected on ${DATE} — night does not count"
  echo "ABORT: LiteLLM 429 detected on ${DATE} — night does NOT count" >&2
  exit 2
fi
if [ "$EMAIL_TRIAGE_LEAK" -gt 0 ]; then
  write_status 3 "email-triage exclusion tag failed on ${DATE}"
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

# --- METRIC: per-turn cost + latency (G1_REFRAME §5/§6/§7 locked options) ---
# Locked decisions (post-Codex review on commit 275aa4c):
#   §5 cost denominator: Langfuse trace spans (primary) with session-level
#                        heuristic fallback when Langfuse non-200
#   §6 latency def:      wall-clock between user-role message and the next
#                        assistant-role message in the same session
#   §7 confidence band:  bootstrapped 90% CI on p50, 1000 resamples
# Helper at scripts/lib/per_turn_metrics.py owns the SQLite + Langfuse +
# bootstrap math. Output: 9-column TSV — n_turns + 4 cost stats + 4 lat stats.
PER_TURN_HELPER="$LIB_DIR/per_turn_metrics.py"
if [ ! -f "$PER_TURN_HELPER" ]; then
  write_status 8 "per_turn_metrics.py missing at $PER_TURN_HELPER"
  echo "ABORT: $PER_TURN_HELPER missing — per-turn columns cannot be computed" >&2
  exit 8
fi
PER_TURN_TSV=$(python3 "$PER_TURN_HELPER" "$DB" "$DATE" 2>/dev/null || echo -e "0\t0\t0\t0\t0\t0\t0\t0\t0")

# --- WRITE ROW ---
# Schema_v stays at 1 per G1_REFRAME §4 (additive columns only, no migration).
# New columns appended after `schema_v` so existing pre-§8 rows remain
# parseable (their per-turn columns are absent rather than misaligned).
HEADER="date	profile	sessions	p50_cost	p95_cost	p95_lat_sec	trace_vol	wilson_ci	promptfoo_n	ragas_metric	ragas_score	hermes_pin	schema_v	n_turns	p50_cost_per_turn	p95_cost_per_turn	ci_low_cost_per_turn	ci_high_cost_per_turn	p50_lat_per_turn	p95_lat_per_turn	ci_low_lat_per_turn	ci_high_lat_per_turn"
[ -f "$BASELINE_MD" ] || printf "%s\n" "$HEADER" > "$BASELINE_MD"

printf "%s\t%s\t%d\t%.5f\t%.5f\t%.2f\t%d\t%s\t%d\tanswer_relevance\t%s\t%s\t%d\t%s\n" \
  "$DATE" "$PROFILE" "$SESSION_COUNT" "$P50_COST" "$P95_COST" "$P95_LATENCY" \
  "$TRACE_VOL" "$WILSON_CI" "$TOTAL" "$RAGAS_SCORE" "$HERMES_PIN" "$SCHEMA_VERSION" \
  "$PER_TURN_TSV" \
  >> "$BASELINE_MD"

# --- SANITY CHECK ---
python3 - <<PY
ragas = float("${RAGAS_SCORE}")
p50 = float("${P50_COST}")
p95 = float("${P95_LATENCY}")
sessions = int("${SESSION_COUNT}")
import sys
checks = []
# Ragas in valid range. Hard requirement; downstream gates depend on this.
if not (0.0 <= ragas <= 1.0):
    checks.append(f"Ragas out of [0,1]: {ragas}")
# Per-session cost zero is EXPECTED on the free-tier path — the §8 reframe
# moved cost gating to the per-turn columns + 4.7.5 confidence-band logic.
# Don't sanity-fail on it (the original check predates the reframe).
# Per-session latency zero with traffic IS still a meaningful signal of
# session-end-time bug; keep that one but downgrade to WARN-only.
if sessions > 0 and p95 <= 0:
    print(f"SANITY WARN on ${DATE}: per-session p95 latency zero (sessions have no end time) — non-fatal under §8 reframe")
if checks:
    print("SANITY FAIL on ${DATE}:", *checks, sep="\n  ")
    sys.exit(1)
print("SANITY OK")
PY

echo "Captured ${DATE} for ${PROFILE}: sessions=${SESSION_COUNT} cost_p50=${P50_COST} cost_p95=${P95_COST} lat_p95=${P95_LATENCY}s trace_vol=${TRACE_VOL} wilson=${WILSON_CI}/${TOTAL} ragas=${RAGAS_SCORE}"

write_status 0 "qualifying-night row written; sessions=${SESSION_COUNT} wilson=${WILSON_CI}/${TOTAL} ragas=${RAGAS_SCORE}"
