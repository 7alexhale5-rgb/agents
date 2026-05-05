#!/usr/bin/env bash
# phase-0-gate-eval.sh — read both soak TSVs at hour 24 and report the gate verdict.
#
# Three measurements:
#   1. Honcho /health 200 continuously for 24h (n ≥ 1440, zero non-200 rows)
#   2. registry-rebuild build_ms p95 < 200ms (n ≥ 288)
#   3. validate-profile.sh --all returns exit 0
#
# Usage: scripts/phase-0-gate-eval.sh [--since YYYY-MM-DDTHH:MM:SSZ]

set -euo pipefail

SINCE="${2:-$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%SZ)}"
HONCHO_TSV="$HOME/Assets/logs/phase-0-honcho-soak.tsv"
REGISTRY_TSV="$HOME/Assets/logs/registry-rebuild.tsv"

echo "Phase 0 gate evaluation — window starts: $SINCE"
echo "================================================"

# Gate 1: Honcho health
if [ ! -f "$HONCHO_TSV" ]; then
  echo "FAIL gate 1: $HONCHO_TSV missing"
  honcho_pass=1
else
  honcho_lines=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since' "$HONCHO_TSV" | wc -l | tr -d ' ')
  honcho_bad=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since && $2 != "200"' "$HONCHO_TSV" | wc -l | tr -d ' ')
  if [ "$honcho_lines" -ge 1440 ] && [ "$honcho_bad" -eq 0 ]; then
    echo "PASS gate 1: Honcho health  n=$honcho_lines  bad=$honcho_bad"
    honcho_pass=0
  else
    echo "FAIL gate 1: Honcho health  n=$honcho_lines (need ≥1440)  bad=$honcho_bad (need 0)"
    honcho_pass=1
  fi
fi

# Gate 2: registry-rebuild p95
if [ ! -f "$REGISTRY_TSV" ]; then
  echo "FAIL gate 2: $REGISTRY_TSV missing"
  registry_pass=1
else
  reg_count=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since' "$REGISTRY_TSV" | wc -l | tr -d ' ')
  if [ "$reg_count" -ge 288 ]; then
    p95=$(awk -F'\t' -v since="$SINCE" 'NR>1 && $1 >= since {print $2}' "$REGISTRY_TSV" | sort -n | awk -v c="$reg_count" 'BEGIN{idx=int(c*0.95)} NR==idx{print; exit}')
    if [ "${p95:-9999}" -lt 200 ]; then
      echo "PASS gate 2: registry rebuild  n=$reg_count  p95=${p95}ms"
      registry_pass=0
    else
      echo "FAIL gate 2: registry rebuild  n=$reg_count  p95=${p95}ms (need <200ms)"
      registry_pass=1
    fi
  else
    echo "FAIL gate 2: registry rebuild  n=$reg_count (need ≥288)"
    registry_pass=1
  fi
fi

# Gate 3: profile validation
if bash "$HOME/Projects/agents/scripts/validate-profile.sh" --all >/dev/null 2>&1; then
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
  echo "Phase 0 GATE: FAIL — $total of 3 gates failed"
  exit 1
fi
