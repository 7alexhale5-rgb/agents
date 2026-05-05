#!/usr/bin/env bash
# phase-0-gate-eval.sh — read soak TSVs and report the Phase 0 gate verdict.
#
# Three measurements (compressed default, --legacy for the original 24h thresholds):
#   1. Honcho /health failure rate
#      compressed: n≥600 + Wilson upper-CI on failure rate ≤0.005
#      legacy:     n≥1440 + zero non-200 rows
#   2. registry-rebuild latency
#      compressed: n≥300 + p95 <200ms + p99 <500ms
#      legacy:     n≥288 + p95 <200ms
#   3. validate-profile.sh --all  → exit 0
#
# Usage:
#   scripts/phase-0-gate-eval.sh                                    # compressed, last 24h
#   scripts/phase-0-gate-eval.sh --since 2026-05-05T19:00:00Z       # explicit window
#   scripts/phase-0-gate-eval.sh --since <ts> --compressed          # explicit compressed
#   scripts/phase-0-gate-eval.sh --since <ts> --legacy              # 24h thresholds

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HONCHO_TSV="$HOME/Assets/logs/phase-0-honcho-soak.tsv"
REGISTRY_TSV="$HOME/Assets/logs/registry-rebuild.tsv"

# Parse args
SINCE=""
MODE="compressed"
while [ $# -gt 0 ]; do
  case "$1" in
    --since) SINCE="$2"; shift 2 ;;
    --compressed) MODE="compressed"; shift ;;
    --legacy) MODE="legacy"; shift ;;
    *) shift ;;
  esac
done

if [ -z "$SINCE" ]; then
  SINCE=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)
fi

# Mode-dependent thresholds
case "$MODE" in
  compressed)
    HONCHO_MIN_N=600
    REGISTRY_MIN_N=300
    HONCHO_DESC="n≥600 + Wilson upper-CI failure rate ≤0.005"
    REGISTRY_DESC="n≥300 + p95 <200ms + p99 <500ms"
    ;;
  legacy)
    HONCHO_MIN_N=1440
    REGISTRY_MIN_N=288
    HONCHO_DESC="n≥1440 + zero non-200 rows"
    REGISTRY_DESC="n≥288 + p95 <200ms"
    ;;
esac

echo "Phase 0 gate evaluation — mode=$MODE  window starts: $SINCE"
echo "================================================"

# --- Gate 1: Honcho health ---
if [ ! -f "$HONCHO_TSV" ]; then
  echo "FAIL gate 1: $HONCHO_TSV missing"
  honcho_pass=1
else
  honcho_n=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since' "$HONCHO_TSV" | wc -l | tr -d ' ')
  honcho_bad=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since && $2 != "200"' "$HONCHO_TSV" | wc -l | tr -d ' ')

  if [ "$MODE" = "compressed" ]; then
    # Wilson upper-CI on failure rate
    upper=$(awk -v k="$honcho_bad" -v n="$honcho_n" 'BEGIN {
      if (n == 0) { print "1.0"; exit }
      z = 1.96
      p = k / n
      denom = 1 + z*z/n
      centre = (p + z*z/(2*n)) / denom
      margin = (z * sqrt((p*(1-p) + z*z/(4*n))/n)) / denom
      hi = centre + margin
      if (hi > 1) hi = 1
      printf "%.5f", hi
    }')
    pass_n="false"; pass_ci="false"
    awk "BEGIN { exit ($honcho_n >= $HONCHO_MIN_N) ? 0 : 1 }" && pass_n="true"
    awk "BEGIN { exit ($upper <= 0.005) ? 0 : 1 }" && pass_ci="true"
    if [ "$pass_n" = "true" ] && [ "$pass_ci" = "true" ]; then
      echo "PASS gate 1: Honcho health  n=$honcho_n  bad=$honcho_bad  Wilson upper=$upper  ($HONCHO_DESC)"
      honcho_pass=0
    else
      echo "FAIL gate 1: Honcho health  n=$honcho_n  bad=$honcho_bad  Wilson upper=$upper  ($HONCHO_DESC)"
      honcho_pass=1
    fi
  else
    if [ "$honcho_n" -ge "$HONCHO_MIN_N" ] && [ "$honcho_bad" -eq 0 ]; then
      echo "PASS gate 1: Honcho health  n=$honcho_n  bad=$honcho_bad  ($HONCHO_DESC)"
      honcho_pass=0
    else
      echo "FAIL gate 1: Honcho health  n=$honcho_n  bad=$honcho_bad  ($HONCHO_DESC)"
      honcho_pass=1
    fi
  fi
fi

# --- Gate 2: registry-rebuild latency ---
if [ ! -f "$REGISTRY_TSV" ]; then
  echo "FAIL gate 2: $REGISTRY_TSV missing"
  registry_pass=1
else
  reg_n=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since' "$REGISTRY_TSV" | wc -l | tr -d ' ')
  if [ "$reg_n" -lt "$REGISTRY_MIN_N" ]; then
    echo "FAIL gate 2: registry rebuild  n=$reg_n  ($REGISTRY_DESC)"
    registry_pass=1
  else
    SORTED=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since {print $2}' "$REGISTRY_TSV" | sort -n)
    p95=$(echo "$SORTED" | awk -v c="$reg_n" 'BEGIN{idx=int(c*0.95); if(idx<1)idx=1} NR==idx{print; exit}')
    p99=$(echo "$SORTED" | awk -v c="$reg_n" 'BEGIN{idx=int(c*0.99); if(idx<1)idx=1} NR==idx{print; exit}')

    if [ "$MODE" = "compressed" ]; then
      if [ "${p95:-9999}" -lt 200 ] && [ "${p99:-9999}" -lt 500 ]; then
        echo "PASS gate 2: registry rebuild  n=$reg_n  p95=${p95}ms  p99=${p99}ms  ($REGISTRY_DESC)"
        registry_pass=0
      else
        echo "FAIL gate 2: registry rebuild  n=$reg_n  p95=${p95}ms  p99=${p99}ms  ($REGISTRY_DESC)"
        registry_pass=1
      fi
    else
      if [ "${p95:-9999}" -lt 200 ]; then
        echo "PASS gate 2: registry rebuild  n=$reg_n  p95=${p95}ms  ($REGISTRY_DESC)"
        registry_pass=0
      else
        echo "FAIL gate 2: registry rebuild  n=$reg_n  p95=${p95}ms  ($REGISTRY_DESC)"
        registry_pass=1
      fi
    fi
  fi
fi

# --- Gate 3: profile validation ---
if bash "$SCRIPT_DIR/validate-profile.sh" --all >/dev/null 2>&1; then
  echo "PASS gate 3: 13 profiles validate clean"
  validate_pass=0
else
  echo "FAIL gate 3: profile validation failed"
  validate_pass=1
fi

echo "================================================"
total=$((honcho_pass + registry_pass + validate_pass))
if [ "$total" -eq 0 ]; then
  echo "Phase 0 GATE: PASS — advance to Phase 1"
  exit 0
else
  echo "Phase 0 GATE: FAIL — $total of 3 gates failed (mode=$MODE)"
  exit 1
fi
