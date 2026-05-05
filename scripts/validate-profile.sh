#!/usr/bin/env bash
# validate-profile.sh — lint a Hermes profile directory against the canonical schema.
# Phase 0 gate primitive: every profile dir must pass before registry-rebuild trusts it.
#
# Required files:
#   SOUL.md, USER.md, MEMORY.md, CLAUDE.md, manifest.json, config.yaml, a2a-card.json
#
# Required directories:
#   rooms/, skills/, workspace/, scratch/, memory/, eval/
#
# manifest.json schema:
#   .sku (string), .tier (1-4 or "TBD"), .channels (array),
#   .memory_axes (array), .guardrails (array), .sla.uptime (number),
#   .sla.p95_latency_seconds (number)
#
# a2a-card.json schema:
#   .agent_id, .description, .side_effects (array), .eval_suite_uri (string|null),
#   .cost_envelope.budget_usd_per_day (number),
#   .cost_envelope.alert_threshold_pct (number)
#
# Usage:
#   scripts/validate-profile.sh <profile-name>
#   scripts/validate-profile.sh --all     # walks all profiles, reports per-profile pass/fail
#
# Exit code: 0 = all pass, 1 = any fail.

set -euo pipefail

PROFILES_DIR="${HERMES_PROFILES_DIR:-$HOME/Projects/agents/hermes/profiles}"

REQUIRED_FILES=(SOUL.md USER.md MEMORY.md CLAUDE.md manifest.json config.yaml a2a-card.json)
REQUIRED_DIRS=(rooms skills workspace scratch memory eval)

validate_one () {
  local name="$1"
  local dir="$PROFILES_DIR/$name"
  local fails=()

  if [ ! -d "$dir" ]; then
    echo "FAIL $name: directory missing ($dir)"
    return 1
  fi

  for f in "${REQUIRED_FILES[@]}"; do
    [ -f "$dir/$f" ] || fails+=("missing-file:$f")
  done

  for d in "${REQUIRED_DIRS[@]}"; do
    [ -d "$dir/$d" ] || fails+=("missing-dir:$d")
  done

  # manifest.json schema
  if [ -f "$dir/manifest.json" ]; then
    if ! jq -e '.sku and (.tier // "TBD") and .channels and .memory_axes and .guardrails and .sla.uptime and .sla.p95_latency_seconds' "$dir/manifest.json" >/dev/null 2>&1; then
      fails+=("manifest.json-schema")
    fi
  fi

  # a2a-card.json schema
  if [ -f "$dir/a2a-card.json" ]; then
    if ! jq -e '.agent_id and .description and (.side_effects | type == "array") and (.eval_suite_uri != null or .eval_suite_uri == null) and .cost_envelope.budget_usd_per_day != null and .cost_envelope.alert_threshold_pct != null' "$dir/a2a-card.json" >/dev/null 2>&1; then
      fails+=("a2a-card-schema")
    fi
    # agent_id must equal profile dir name
    local aid
    aid=$(jq -r '.agent_id' "$dir/a2a-card.json" 2>/dev/null || echo '')
    [ "$aid" = "$name" ] || fails+=("a2a-card-agent-id-mismatch:$aid")
  fi

  if [ ${#fails[@]} -eq 0 ]; then
    echo "PASS $name"
    return 0
  else
    echo "FAIL $name: ${fails[*]}"
    return 1
  fi
}

if [ "${1:-}" = "--all" ]; then
  total=0; passed=0; failed=0
  for d in "$PROFILES_DIR"/*/; do
    [ -d "$d" ] || continue
    n=$(basename "$d")
    total=$((total + 1))
    if validate_one "$n"; then
      passed=$((passed + 1))
    else
      failed=$((failed + 1))
    fi
  done
  echo "----"
  echo "Total: $total · Passed: $passed · Failed: $failed"
  [ "$failed" -eq 0 ]
elif [ -n "${1:-}" ]; then
  validate_one "$1"
else
  echo "usage: $0 <profile-name> | $0 --all" >&2
  exit 2
fi
