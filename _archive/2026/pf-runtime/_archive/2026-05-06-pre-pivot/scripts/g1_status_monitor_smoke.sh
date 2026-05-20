#!/usr/bin/env bash
# Smoke test for scripts/g1-status-monitor.sh.
#
# RED phase test, written before the implementation. Asserts the contract:
#
#   1. When a fresh `_status` file with `exit_code=0` exists for $TODAY,
#      the monitor emits NO alert and exits 0.
#   2. When `_status` file is missing for $TODAY (capture didn't fire),
#      the monitor stages an alert payload and exits 1.
#   3. When `_status` file shows `exit_code != 0`, the monitor stages
#      an alert payload and exits 1.
#   4. When the monitor stages an alert, the payload contains the date
#      and the failure reason in plain text (not JSON, not jargon).
#
# The monitor uses a STAGE_DIR for outbound alert payloads. In production
# this dir is read by a separate Slack-poster step. Tests assert against
# the staged payload, not against Slack itself.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MONITOR="$REPO_ROOT/scripts/g1-status-monitor.sh"

[ -f "$MONITOR" ] || { echo "FAIL: monitor script missing at $MONITOR"; exit 4; }

# Sandbox dirs — keep tests isolated from real ~/.hermes and ~/Assets.
TMPROOT=$(mktemp -d /tmp/g1-monitor-test-XXXXXX)
trap 'rm -rf "$TMPROOT"' EXIT

STATUS_DIR="$TMPROOT/status"
STAGE_DIR="$TMPROOT/alerts"
mkdir -p "$STATUS_DIR" "$STAGE_DIR"
TODAY=$(date -u +%Y-%m-%d)

PASSED=0
FAILED=0

assert() {
  local name="$1"; local cmd="$2"
  if eval "$cmd"; then
    echo "PASS: $name"
    PASSED=$((PASSED + 1))
  else
    echo "FAIL: $name"
    FAILED=$((FAILED + 1))
  fi
}

# --- Test 1: clean status, no alert ---
rm -f "$STAGE_DIR"/*.txt
cat > "$STATUS_DIR/${TODAY}.status" <<EOF
date=${TODAY}
exit_code=0
profile=personal
ran_at=2026-05-06T02:30:00Z
sessions=2
EOF
G1_STATUS_DIR="$STATUS_DIR" G1_ALERT_STAGE_DIR="$STAGE_DIR" G1_ALERT_DISABLE_SLACK=1 \
  bash "$MONITOR" >/dev/null 2>&1
EXIT_CLEAN=$?
ALERTS_CLEAN=$(find "$STAGE_DIR" -type f -name "*.txt" 2>/dev/null | wc -l | tr -d ' ')
assert "clean status -> exit 0" "[ $EXIT_CLEAN -eq 0 ]"
assert "clean status -> 0 alerts staged" "[ $ALERTS_CLEAN -eq 0 ]"

# --- Test 2: missing status file, alert + exit 1 ---
rm -f "$STATUS_DIR"/*.status "$STAGE_DIR"/*.txt
set +e
G1_STATUS_DIR="$STATUS_DIR" G1_ALERT_STAGE_DIR="$STAGE_DIR" G1_ALERT_DISABLE_SLACK=1 \
  bash "$MONITOR" >/dev/null 2>&1
EXIT_MISSING=$?
set -e
ALERTS_MISSING=$(find "$STAGE_DIR" -type f -name "*.txt" 2>/dev/null | wc -l | tr -d ' ')
assert "missing status -> exit 1" "[ $EXIT_MISSING -eq 1 ]"
assert "missing status -> 1 alert staged" "[ $ALERTS_MISSING -eq 1 ]"

# --- Test 3: failed status (exit_code != 0), alert + exit 1 ---
rm -f "$STAGE_DIR"/*.txt
cat > "$STATUS_DIR/${TODAY}.status" <<EOF
date=${TODAY}
exit_code=4
profile=personal
ran_at=2026-05-06T02:30:00Z
reason=DB missing at /Users/alexhale/.hermes/profiles/personal/state.db
EOF
set +e
G1_STATUS_DIR="$STATUS_DIR" G1_ALERT_STAGE_DIR="$STAGE_DIR" G1_ALERT_DISABLE_SLACK=1 \
  bash "$MONITOR" >/dev/null 2>&1
EXIT_FAILED=$?
set -e
ALERTS_FAILED=$(find "$STAGE_DIR" -type f -name "*.txt" 2>/dev/null | wc -l | tr -d ' ')
assert "failed status -> exit 1" "[ $EXIT_FAILED -eq 1 ]"
assert "failed status -> 1 alert staged" "[ $ALERTS_FAILED -eq 1 ]"

# --- Test 4: alert payload format (date + reason in plain text) ---
# Use direct grep on the staged file — avoid heredoc/eval re-expansion of
# any literal `$VARNAME` tokens that may appear in the payload (e.g. the
# runbook line which references env-var names by name).
PAYLOAD_FILE=$(find "$STAGE_DIR" -type f -name "*.txt" | head -1)
if grep -qF "$TODAY" "$PAYLOAD_FILE"; then
  echo "PASS: payload contains date"; PASSED=$((PASSED + 1))
else
  echo "FAIL: payload contains date"; FAILED=$((FAILED + 1))
fi
if grep -qFi 'db missing' "$PAYLOAD_FILE"; then
  echo "PASS: payload contains reason text"; PASSED=$((PASSED + 1))
else
  echo "FAIL: payload contains reason text"; FAILED=$((FAILED + 1))
fi
if grep -qF 'personal' "$PAYLOAD_FILE"; then
  echo "PASS: payload contains profile name"; PASSED=$((PASSED + 1))
else
  echo "FAIL: payload contains profile name"; FAILED=$((FAILED + 1))
fi

# --- Summary ---
echo
echo "Smoke results: $PASSED passed, $FAILED failed"
[ "$FAILED" -eq 0 ]
