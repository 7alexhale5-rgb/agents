#!/usr/bin/env bash
# phase-0-soak-tick.sh — single-tick of the 24h Honcho health soak.
# Probes localhost:8765/health and appends one row to ~/Assets/logs/phase-0-honcho-soak.tsv.
# Schedule: launchd com.prettyfly.phase-0-soak (StartInterval=60).
#
# Schema (TSV):
#   ts \t status_code \t latency_ms \t body_ok
#
# Gate eval (at hour 24): zero rows with status_code != 200, n ≥ 1440.

set -euo pipefail

LOG_DIR="$HOME/Assets/logs"
TSV="$LOG_DIR/phase-0-honcho-soak.tsv"

mkdir -p "$LOG_DIR"

# Header (write once)
[ -f "$TSV" ] || echo -e "ts\tstatus_code\tlatency_ms\tbody_ok" > "$TSV"

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Probe with 5s timeout; capture status + latency in one curl pass.
# %{http_code} \t %{time_total}
out=$(curl -sS -m 5 -o /tmp/honcho-soak-body.$$ -w '%{http_code}\t%{time_total}' http://localhost:8765/health 2>/dev/null || echo -e "000\t0.000")
status="${out%%	*}"
latency_s="${out#*	}"
latency_ms=$(awk -v s="$latency_s" 'BEGIN { printf "%d", s*1000 }')

body_ok="false"
if [ -f /tmp/honcho-soak-body.$$ ] && grep -q '"status".*"ok"' /tmp/honcho-soak-body.$$ 2>/dev/null; then
  body_ok="true"
fi
rm -f /tmp/honcho-soak-body.$$

echo -e "${ts}\t${status}\t${latency_ms}\t${body_ok}" >> "$TSV"
