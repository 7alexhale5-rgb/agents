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
  post_alert_to_slack "$reason" "$profile" || echo "warn: Slack post failed (alert still staged)"
}

# Post the alert directly to Iris's DM with alex via Slack chat.postMessage.
# Decoupled from the file staging — file always lands; Slack post is best-effort.
# Requires SLACK_BOT_TOKEN in env (loaded from ~/.hermes/.env at run time).
# Set G1_ALERT_DISABLE_SLACK=1 to skip (e.g. during fixture tests).
post_alert_to_slack() {
  if [ "${G1_ALERT_DISABLE_SLACK:-0}" = "1" ]; then
    return 0
  fi
  local reason="$1"
  local profile="$2"
  # Token lives in the per-profile .env (gateway loads it at request time
  # via dotenv). Fall back to the global ~/.hermes/.env if the profile
  # one is absent (rare — flagged via warn).
  local hermes_env=""
  for candidate in "${HOME}/.hermes/profiles/${profile}/.env" "${HOME}/.hermes/.env"; do
    if [ -f "$candidate" ]; then
      hermes_env="$candidate"
      break
    fi
  done
  if [ -z "$hermes_env" ]; then
    echo "warn: no .env found in profiles/${profile}/ or .hermes root; skipping Slack post"
    return 1
  fi
  local token
  token=$(awk -F= '/^SLACK_BOT_TOKEN=/{sub(/^SLACK_BOT_TOKEN=/,""); print; exit}' "$hermes_env" 2>/dev/null)
  if [ -z "$token" ]; then
    echo "warn: SLACK_BOT_TOKEN not found in $hermes_env; skipping Slack post"
    return 1
  fi
  local channel="${G1_ALERT_SLACK_CHANNEL:-D0B28352A3T}"
  local text=":rotating_light: G1 baseline capture alert for ${TARGET_DATE}
profile: ${profile}
reason: ${reason}
runbook: tail ~/Assets/logs/g1-baseline-capture.log; cat ~/Assets/logs/g1-status/${TARGET_DATE}.status"
  # Use a heredoc + jq to JSON-escape safely.
  local payload
  payload=$(jq -n --arg channel "$channel" --arg text "$text" '{channel: $channel, text: $text}' 2>/dev/null)
  if [ -z "$payload" ]; then
    echo "warn: jq missing or payload build failed; skipping Slack post"
    return 1
  fi
  local response
  response=$(curl -sS --max-time 10 -X POST https://slack.com/api/chat.postMessage \
    -H "Authorization: Bearer ${token}" \
    -H "Content-Type: application/json; charset=utf-8" \
    -d "$payload" 2>&1) || {
      echo "warn: Slack curl failed: $response"
      return 1
    }
  if echo "$response" | grep -q '"ok":true'; then
    echo "Slack alert posted to ${channel}"
    return 0
  fi
  echo "warn: Slack returned non-ok: $response"
  return 1
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
