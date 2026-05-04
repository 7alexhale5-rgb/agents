#!/usr/bin/env bash
# email-triage-eval-nightly.sh
# Runs the email-triage Promptfoo golden-set eval nightly. Karpathy P1 acceptance:
# 7 consecutive nights at ≥0.85 advances to P2/P3.
#
# Schedule: 02:00 ET via launchd com.prettyfly.email-triage-eval-nightly.plist
# Output:   reports/{date}.json (gitignored — drift signal lives in runs/, not reports/)
# Pass-rate tracking: appended to runs/_nightly-history.tsv (date \t provider \t pass_rate \t total)

set -euo pipefail

EVAL_DIR="/Users/alexhale/Projects/agents/marketplace/manifests/email-triage/eval-suite"
LOG_FILE="/Users/alexhale/Assets/logs/email-triage-eval-nightly.log"
HISTORY="${EVAL_DIR}/runs/_nightly-history.tsv"
DATE=$(date +%Y-%m-%d)

mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "${EVAL_DIR}/runs"

echo "=== email-triage eval ${DATE} $(date +%H:%M:%S) ===" >> "$LOG_FILE"

# Load API keys (Mistral / Anthropic / OpenRouter / NVIDIA — whichever are funded)
set -a
# shellcheck disable=SC1091
source /Users/alexhale/.config/api-keys.env 2>/dev/null || true
set +a

cd "$EVAL_DIR"

# Probe which provider has credit before running the full eval.
# Fall through Mistral -> Anthropic -> OpenRouter; whichever responds first wins.
PROVIDER=""
for candidate in "mistral:mistral-medium-latest" "anthropic:claude-sonnet-4-6" "openrouter:nvidia/nemotron-nano-9b-v2"; do
  # 1-shot probe: a single tiny eval against the first golden line
  if promptfoo eval \
       --filter-providers "$candidate" \
       --filter-tests-pattern "$(head -1 golden.jsonl | head -c 40)" \
       --no-cache \
       -o /tmp/email-triage-probe.json 2>>"$LOG_FILE" >/dev/null; then
    if jq -e '.results.stats.errors == 0' /tmp/email-triage-probe.json >/dev/null 2>&1; then
      PROVIDER="$candidate"
      break
    fi
  fi
done

if [ -z "$PROVIDER" ]; then
  echo "ALL PROVIDERS UNFUNDED at ${DATE}; skipping eval. Refill credits to resume nightly." | tee -a "$LOG_FILE"
  exit 0
fi

echo "Using provider: $PROVIDER" >> "$LOG_FILE"

# Full eval against 30 golden cases
REPORT="reports/${DATE}.json"
promptfoo eval \
  --filter-providers "$PROVIDER" \
  -o "$REPORT" \
  --no-cache 2>>"$LOG_FILE" >>"$LOG_FILE"

# Extract pass rate
PASS=$(jq -r '.results.stats.successes' "$REPORT")
FAIL=$(jq -r '.results.stats.failures' "$REPORT")
ERRORS=$(jq -r '.results.stats.errors' "$REPORT")
TOTAL=$((PASS + FAIL + ERRORS))
RATE=$(awk -v p="$PASS" -v t="$TOTAL" 'BEGIN { if (t > 0) printf "%.4f", p/t; else print "0.0000" }')

# Append to history TSV
[ -f "$HISTORY" ] || echo -e "date\tprovider\tpass_rate\tpassed\ttotal" > "$HISTORY"
echo -e "${DATE}\t${PROVIDER}\t${RATE}\t${PASS}\t${TOTAL}" >> "$HISTORY"

echo "Result: ${PASS}/${TOTAL} = ${RATE} on ${PROVIDER}" >> "$LOG_FILE"

# Karpathy P1 gate: ≥0.85 expected. Below = log a warning; below 3 nights running = vanclief P1 alert.
if awk -v r="$RATE" 'BEGIN { exit !(r < 0.85) }'; then
  echo "WARN: pass-rate ${RATE} below 0.85 floor" >> "$LOG_FILE"
  # Count consecutive sub-floor nights
  RECENT_LOW=$(tail -7 "$HISTORY" | awk -F'\t' 'NR>1 && $3<0.85 {c++} END {print c+0}')
  if [ "${RECENT_LOW:-0}" -ge 3 ]; then
    echo "ALERT: ${RECENT_LOW} of last 7 nights below 0.85 — vanclief should draft fix PR" >> "$LOG_FILE"
    # TODO when vanclief profile is live: post to its alert channel
  fi
fi

echo "" >> "$LOG_FILE"
