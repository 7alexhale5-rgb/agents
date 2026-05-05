#!/usr/bin/env bash
# phase-0-soak-compressed.sh — 60-min wall-clock Phase 0 soak.
#
# Same falsifiable measurements as the 24h launchd soak, statistically equal
# or stronger via tighter cadence. Both runs write to the same TSVs and
# cross-validate; the launchd soak keeps running in parallel.
#
# Probes:
#   - Honcho /health every 4s × 900 samples = 60 min
#     Gate: Wilson upper-CI on failure rate ≤ 0.005 (true rate <0.5% w/ 95% conf)
#   - registry-rebuild.py 300× across mixed gap distribution (cold/warm mix)
#     Gate: p95 <200ms AND p99 <500ms
#
# Output: stdout running log + ~/Assets/logs/phase-0-soak-compressed.log
#         + appended rows in phase-0-honcho-soak.tsv + registry-rebuild.tsv
#
# Exit code: 0 if compressed gate clears, 1 if any gate fails.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG="$HOME/Assets/logs/phase-0-soak-compressed.log"
START_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

mkdir -p "$(dirname "$LOG")"
{
  echo "================================================"
  echo "compressed soak started: $START_TS"
  echo "================================================"
} | tee -a "$LOG"

# --- Honcho probe stream: 4s cadence × 900 samples ---
(
  for _ in $(seq 1 900); do
    bash "$SCRIPT_DIR/phase-0-soak-tick.sh" >/dev/null 2>&1 || true
    sleep 4
  done
) &
HONCHO_PID=$!
echo "honcho probe stream started: pid=$HONCHO_PID  (4s × 900 = 60min)" | tee -a "$LOG"

# --- Registry rebuild stream: 300 fires across mixed gaps ---
echo "registry burst 1: 100 zero-gap (warm-cache distribution)" | tee -a "$LOG"
for _ in $(seq 1 100); do
  python3 "$SCRIPT_DIR/registry-rebuild.py" --tsv >/dev/null 2>&1 || true
done

echo "registry burst 2: 100 × 6s gap" | tee -a "$LOG"
for _ in $(seq 1 100); do
  python3 "$SCRIPT_DIR/registry-rebuild.py" --tsv >/dev/null 2>&1 || true
  sleep 6
done

echo "registry burst 3: 100 × 30s gap (cold-cache distribution)" | tee -a "$LOG"
for _ in $(seq 1 100); do
  python3 "$SCRIPT_DIR/registry-rebuild.py" --tsv >/dev/null 2>&1 || true
  sleep 30
done

echo "registry stream done; waiting on honcho probe..." | tee -a "$LOG"
wait "$HONCHO_PID"

END_TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
{
  echo "================================================"
  echo "compressed soak completed: $END_TS"
  echo "window: $START_TS .. $END_TS"
} | tee -a "$LOG"

# --- Gate evaluation against the compressed window ---
echo "------------------------------------------------" | tee -a "$LOG"
bash "$SCRIPT_DIR/phase-0-gate-eval.sh" --since "$START_TS" --compressed | tee -a "$LOG"
GATE_EXIT=${PIPESTATUS[0]}

exit "$GATE_EXIT"
