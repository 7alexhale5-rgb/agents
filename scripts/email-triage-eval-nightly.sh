#!/usr/bin/env bash
# email-triage-eval-nightly.sh
# Runs the email-triage Promptfoo golden-set eval. Karpathy P1 gate (revised 2026-05-04):
#   - In-run statistical stability via repeat=5 (150 trials/provider) + ≥2 funded providers.
#   - Wilson lower-CI ≥0.80 AND median ≥0.85 across providers = P1 cleared.
#   - Calendar separation no longer required — reps + multi-provider give the same property.
#
# Schedule: 02:00 ET via launchd com.prettyfly.email-triage-eval-nightly.plist
# Output:   reports/{date}-{provider}.json (gitignored)
# Tracking: runs/_nightly-history.tsv (date \t provider \t pass_rate \t passed \t total \t lower_ci)

set -euo pipefail

EVAL_DIR="/Users/alexhale/Projects/agents/marketplace/manifests/email-triage/eval-suite"
LOG_FILE="/Users/alexhale/Assets/logs/email-triage-eval-nightly.log"
HISTORY="${EVAL_DIR}/runs/_nightly-history.tsv"
DATE=$(date +%Y-%m-%d)
TS=$(date +%H:%M:%S)

mkdir -p "$(dirname "$LOG_FILE")"
mkdir -p "${EVAL_DIR}/runs"

echo "=== email-triage eval ${DATE} ${TS} ===" >> "$LOG_FILE"

# Load API keys (Mistral / Anthropic / OpenRouter / NVIDIA — whichever are funded)
set -a
# shellcheck disable=SC1091
source /Users/alexhale/.config/api-keys.env 2>/dev/null || true
set +a

cd "$EVAL_DIR"

# Render config with envsubst — promptfoo 0.121.5 doesn't substitute ${VAR} in apiKey fields.
# Render alongside the original so file:// paths in the YAML resolve correctly.
# Ephemeral; trap removes on exit. .gitignore'd via the .rendered- prefix pattern.
RENDERED_CONFIG="${EVAL_DIR}/.rendered-promptfoo-$$.yaml"
trap 'rm -f "$RENDERED_CONFIG" /tmp/probe-*.json' EXIT
envsubst < promptfooconfig.yaml > "$RENDERED_CONFIG"
chmod 600 "$RENDERED_CONFIG"

# Header (run once)
[ -f "$HISTORY" ] || echo -e "date\tprovider\tpass_rate\tpassed\ttotal\tlower_ci" > "$HISTORY"

# Wilson lower-CI math factored out into scripts/lib/wilson.sh — single source of truth.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/lib/wilson.sh"

run_provider () {
  local CANDIDATE="$1"
  local SAFE_NAME
  SAFE_NAME=$(echo "$CANDIDATE" | tr '/:' '__')
  local REPORT="reports/${DATE}-${SAFE_NAME}.json"

  echo "--- probing ${CANDIDATE} ---" >> "$LOG_FILE"

  # Single-trial probe with hard 90s ceiling (perl alarm — macOS lacks `timeout`).
  # --repeat 1 overrides config's global repeat=5; probe shouldn't spend 5 calls on cold-start NIM.
  perl -e 'alarm 90; exec @ARGV' -- promptfoo eval \
      -c "$RENDERED_CONFIG" \
      --filter-providers "$CANDIDATE" \
      --filter-first-n 1 \
      --repeat 1 \
      --no-cache \
      -o "/tmp/probe-${SAFE_NAME}.json" 2>>"$LOG_FILE" >/dev/null || true
  if [ ! -f "/tmp/probe-${SAFE_NAME}.json" ]; then
    echo "  probe timed out or never wrote output" >> "$LOG_FILE"
    return 1
  fi
  if ! jq -e '.results.stats.errors == 0' "/tmp/probe-${SAFE_NAME}.json" >/dev/null 2>&1; then
    echo "  probe returned errors (zero balance, bad model id, or transport failure)" >> "$LOG_FILE"
    return 1
  fi

  echo "  funded — running full eval (repeat=5)" >> "$LOG_FILE"
  # promptfoo exits non-zero whenever any test fails — that's expected, not a wrapper failure.
  # Trust the JSON report instead of the exit code.
  promptfoo eval \
      -c "$RENDERED_CONFIG" \
      --filter-providers "$CANDIDATE" \
      --repeat 5 \
      -o "$REPORT" \
      --no-cache 2>>"$LOG_FILE" >>"$LOG_FILE" || true

  if [ ! -f "$REPORT" ]; then
    echo "  full eval produced no report file" >> "$LOG_FILE"
    return 1
  fi

  local PASS FAIL ERRORS TOTAL RATE LOWER
  PASS=$(jq -r '.results.stats.successes // 0' "$REPORT")
  FAIL=$(jq -r '.results.stats.failures // 0' "$REPORT")
  ERRORS=$(jq -r '.results.stats.errors // 0' "$REPORT")
  TOTAL=$((PASS + FAIL + ERRORS))
  if [ "$TOTAL" -eq 0 ]; then
    echo "  zero-trial result — provider returned nothing" >> "$LOG_FILE"
    return 1
  fi
  RATE=$(awk -v p="$PASS" -v t="$TOTAL" 'BEGIN { printf "%.4f", p/t }')
  LOWER=$(wilson_lower "$PASS" "$TOTAL")

  echo -e "${DATE}\t${CANDIDATE}\t${RATE}\t${PASS}\t${TOTAL}\t${LOWER}" >> "$HISTORY"
  echo "  ${PASS}/${TOTAL} = ${RATE} (lower-CI ${LOWER}) on ${CANDIDATE}" >> "$LOG_FILE"

  # Publish eval_trace to the agora (Phase 1 substrate-as-bus claim).
  # Failure must not break the eval — `|| true`. Trace lands in
  # workspace=prettyfly-os, session=eval-traces-{YYYY-MM}, peer=vanclief.
  MANIFEST_HASH=$(sha256sum "$RENDERED_CONFIG" 2>/dev/null | cut -d' ' -f1 || shasum -a 256 "$RENDERED_CONFIG" 2>/dev/null | cut -d' ' -f1)
  TRACE_JSON=$(jq -n \
    --arg sku "email-triage" \
    --arg provider "$CANDIDATE" \
    --arg date "$DATE" \
    --argjson passed "$PASS" \
    --argjson total "$TOTAL" \
    --argjson rate "$RATE" \
    --argjson lower "$LOWER" \
    --arg hash "${MANIFEST_HASH:-unknown}" \
    --arg report "$REPORT" \
    '{event_type:"eval_trace", sku:$sku, provider:$provider, date:$date,
      passed:$passed, total:$total, rate:$rate, wilson_lower_ci:$lower,
      manifest_hash:$hash, report_path:$report}')
  # Invoke the publish script directly (its shebang pins /usr/bin/python3 — the
  # only macOS python3 with PyJWT installed; launchd's PATH resolves a broken
  # /opt/homebrew/bin/python3 first which silently swallows the trace via || true).
  echo "$TRACE_JSON" | "$SCRIPT_DIR/honcho-publish-eval-trace.py" >>"$LOG_FILE" 2>&1 || true

  return 0
}

# Run providers sequentially. Parallel saturates free-tier rate budgets (NIM 429s under
# concurrent load, Mistral 429s if multiple workers fire at once). Sequential ~5-10 min total
# for a nightly cron is fine; in-run repeat=5 gives the statistical signal in one pass anyway.
for CANDIDATE in \
    "mistral:mistral-medium-latest" \
    "openai:chat:nvidia/llama-3.1-nemotron-nano-8b-v1" \
    "anthropic:claude-sonnet-4-6" \
    "openrouter:nvidia/nemotron-nano-9b-v2"; do
  run_provider "$CANDIDATE" || true
done

# Summarise this run's outcomes
RUN_ROWS=$(awk -F'\t' -v d="$DATE" 'NR>1 && $1==d {print}' "$HISTORY")
FUNDED_COUNT=$(echo "$RUN_ROWS" | grep -c . || echo 0)
echo "Run summary: ${FUNDED_COUNT} funded provider(s) reported for ${DATE}" >> "$LOG_FILE"

if [ "$FUNDED_COUNT" -eq 0 ]; then
  echo "ALL PROVIDERS UNFUNDED at ${DATE}; refill credits to resume nightly." >> "$LOG_FILE"
fi

# Karpathy P1 gate (in-run): ≥2 providers, each with lower-CI ≥0.80 and rate ≥0.85
PASS_GATE=$(echo "$RUN_ROWS" | awk -F'\t' '$3>=0.85 && $6>=0.80 {c++} END {print c+0}')
if [ "${PASS_GATE:-0}" -ge 2 ]; then
  echo "P1 GATE CLEARED: ${PASS_GATE} providers ≥0.85 with lower-CI ≥0.80" >> "$LOG_FILE"
fi

echo "" >> "$LOG_FILE"
