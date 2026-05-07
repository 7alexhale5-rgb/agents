#!/usr/bin/env bash
# g1-status-monitor.sh — Phase 4.7 G1 capture observability layer.
#
# Reads today's status file written by `scripts/g1-baseline-capture.sh`
# (capture fires at 02:30 local, monitor at 09:00 local — same calendar
# day under normal operation). Stages a Slack alert payload at
# "$G1_ALERT_STAGE_DIR/${TARGET_DATE}.txt" if the capture failed or
# didn't fire. A separate launchd job posts the staged payloads to Slack
# (decoupled so this monitor is offline-testable).
#
# DST / timezone edge: launchd `StartCalendarInterval` fires in local
# time but the script computes UTC date. On most days these are the same
# UTC calendar day; DST transitions and offset≥6h timezones can produce
# a 1-hour window where the local schedule fires on a different UTC date.
# Pass an explicit YYYY-MM-DD as the first arg to override the default.
#
# Per the G1 reframe plan §3am-test row "G1 night-1 capture row missing":
# silent failure of a nightly capture is the highest-leverage observability
# gap. This script closes it.
#
# Wire:
#   - `g1-baseline-capture.sh` writes "$G1_STATUS_DIR/$DATE.status" with
#     `exit_code`, `profile`, `ran_at`, `sessions`, optional `reason`.
#   - `g1-status-monitor.sh` (this file) runs daily at 09:00 ET via
#     `com.prettyfly.g1-status-monitor.plist`. Reads yesterday's status,
#     stages an alert if missing or non-zero exit.
#   - A future Slack-poster job (out of scope here) drains
#     "$G1_ALERT_STAGE_DIR/*.txt" and posts to @iris.
#
# Env (override for tests):
#   G1_STATUS_DIR        — where capture writes status files (default: ~/Assets/logs/g1-status)
#   G1_ALERT_STAGE_DIR   — where monitor stages alert payloads (default: ~/Assets/logs/g1-alerts)
#
# Exit codes:
#   0 — yesterday's status was clean (no alert needed)
#   1 — alert staged (missing status OR non-zero exit_code)
#   2 — pre-flight failure (status dir unreadable, etc.)

set -euo pipefail

STATUS_DIR="${G1_STATUS_DIR:-$HOME/Assets/logs/g1-status}"
STAGE_DIR="${G1_ALERT_STAGE_DIR:-$HOME/Assets/logs/g1-alerts}"
TARGET_DATE="${1:-$(date -u +%Y-%m-%d)}"

mkdir -p "$STATUS_DIR" "$STAGE_DIR" 2>/dev/null || { echo "ABORT: cannot create dirs"; exit 2; }

STATUS_FILE="$STATUS_DIR/${TARGET_DATE}.status"
ALERT_FILE="$STAGE_DIR/${TARGET_DATE}.txt"

stage_alert() {
  local reason="$1"
  local profile="${2:-unknown}"
  cat > "$ALERT_FILE" <<EOF
G1 baseline capture alert for ${TARGET_DATE}
profile: ${profile}
reason: ${reason}
staged_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
runbook: scripts/g1-baseline-capture.sh logs at \$G1_STATUS_DIR/${TARGET_DATE}.status
EOF
  echo "alert staged at $ALERT_FILE"
}

if [ ! -f "$STATUS_FILE" ]; then
  stage_alert "no status file written for ${TARGET_DATE} — capture script did not run, or status_dir mismatch" "personal"
  exit 1
fi

# Parse status file (key=value lines).
EXIT_CODE=$(awk -F= '/^exit_code=/{print $2; exit}' "$STATUS_FILE" 2>/dev/null || echo "")
PROFILE=$(awk -F= '/^profile=/{print $2; exit}' "$STATUS_FILE" 2>/dev/null || echo "unknown")
REASON=$(awk -F= '/^reason=/{sub(/^reason=/,""); print; exit}' "$STATUS_FILE" 2>/dev/null || echo "")

if [ -z "$EXIT_CODE" ]; then
  stage_alert "status file at $STATUS_FILE has no exit_code field — corrupt or partial write" "$PROFILE"
  exit 1
fi

if [ "$EXIT_CODE" != "0" ]; then
  REASON="${REASON:-non-zero exit_code=$EXIT_CODE; check capture log}"
  stage_alert "$REASON" "$PROFILE"
  exit 1
fi

echo "clean: ${TARGET_DATE} ${PROFILE} exit_code=0"
exit 0
