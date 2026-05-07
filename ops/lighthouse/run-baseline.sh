#!/bin/bash
# Regenerate the Lighthouse baseline. Standalone — only needs node + npm (for
# `npx lighthouse`). Override via env vars: LH_TARGET_URL, LH_ROUTES, LH_RUNS.
set -euo pipefail

TARGET_URL="${LH_TARGET_URL:-http://localhost:3000}"
ROUTES="${LH_ROUTES:-/}"
RUNS="${LH_RUNS:-3}"

if [[ -z "${CHROME_PATH:-}" ]]; then
  if [[ -d "/Applications/Google Chrome.app" ]]; then
    export CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  elif command -v google-chrome >/dev/null 2>&1; then
    export CHROME_PATH="$(command -v google-chrome)"
  fi
fi

OUT_DIR="ops/lighthouse/baseline"
RAW_DIR="$OUT_DIR/.raw"
mkdir -p "$RAW_DIR"
rm -f "$RAW_DIR"/*.json 2>/dev/null || true

for route in $ROUTES; do
  slug=$(echo "$route" | sed 's|^/||; s|/|-|g')
  [[ -z "$slug" ]] && slug="home"
  echo "[$slug] $route ($RUNS runs)"
  for run in $(seq 1 "$RUNS"); do
    npx --no-install lighthouse "${TARGET_URL}${route}" \
      --output=json --output-path="$RAW_DIR/$slug.$run.json" \
      --chrome-flags="--headless=new --no-sandbox" --quiet \
      --only-categories=performance,accessibility,best-practices,seo \
      >/dev/null 2>&1 || echo "  run $run failed"
  done
done

node "$(cd "$(dirname "$0")" && pwd)/summarize.mjs" --raw-dir "$RAW_DIR" --out-dir "$OUT_DIR"
echo "baseline refreshed at $OUT_DIR/"
