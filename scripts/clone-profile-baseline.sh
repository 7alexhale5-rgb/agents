#!/usr/bin/env bash
# clone-profile-baseline.sh — Phase 4.7 plan §5.2
#
# Clone a Hermes profile into a sibling baseline workspace for shadow-mode
# measurement. Used by:
#   - Phase 4.7 G1 (clone `personal` → `personal-baseline` for the 7-night window)
#   - Phase 4.7.4 atlas-ceo mid-pilot (per PLAN.md §10 pilot ladder)
#
# Idempotent — running twice is a no-op on the second run (skips clone, skips
# key mint, re-runs validation).
#
# Usage:
#   scripts/clone-profile-baseline.sh <source-profile> <target-baseline>
#
# Examples:
#   scripts/clone-profile-baseline.sh personal personal-baseline
#   scripts/clone-profile-baseline.sh atlas-ceo atlas-ceo-pilot
#
# Pre-conditions:
#   - Source profile dir exists at ~/.hermes/profiles/<source>/
#   - LiteLLM is reachable at 127.0.0.1:4000 (or skip key mint with --no-litellm)
#   - validate-profile.sh exists at scripts/validate-profile.sh
#
# Exit codes:
#   0 — clone + key mint + validation succeeded
#   1 — bad arguments
#   2 — source profile missing
#   3 — validation failed against the cloned dir

set -euo pipefail

usage() {
  echo "usage: $0 <source-profile> <target-baseline> [--no-litellm]" >&2
  echo "  --no-litellm   skip LiteLLM key mint (for offline / pre-Docker bring-up)" >&2
  exit 1
}

[ "$#" -ge 2 ] || usage

SRC="$1"
DST="$2"
SKIP_LITELLM=0
if [ "${3:-}" = "--no-litellm" ]; then
  SKIP_LITELLM=1
fi

PROFILES_ROOT="$HOME/.hermes/profiles"
SRC_DIR="$PROFILES_ROOT/$SRC"
DST_DIR="$PROFILES_ROOT/$DST"
REPO_ROOT="$HOME/Projects/agents"
VALIDATE_SCRIPT="$REPO_ROOT/scripts/validate-profile.sh"

[ -d "$SRC_DIR" ] || { echo "ABORT: source profile dir missing at $SRC_DIR" >&2; exit 2; }

# Step 1: clone (idempotent — skip if dst exists)
if [ -d "$DST_DIR" ]; then
  echo "skip: $DST_DIR already exists"
else
  echo "clone: cp -R $SRC_DIR -> $DST_DIR"
  cp -R "$SRC_DIR" "$DST_DIR"
fi

# Step 2: mint LiteLLM key alias (raised cap per plan §4.4 cost math)
KEY_ALIAS="${DST}-tier-cheap"
KEY_MAX_BUDGET=7
KEY_DAILY_BUDGET="1.00"  # raised from 0.30 in original plan per §4.4

if [ "$SKIP_LITELLM" -eq 1 ]; then
  echo "skip: --no-litellm flag — not minting key alias $KEY_ALIAS"
elif command -v litellm-cli >/dev/null 2>&1; then
  if litellm-cli key list 2>/dev/null | grep -q "$KEY_ALIAS"; then
    echo "skip: LiteLLM key alias $KEY_ALIAS already exists"
  else
    echo "mint: LiteLLM key alias=$KEY_ALIAS budget=\$$KEY_MAX_BUDGET daily=\$$KEY_DAILY_BUDGET"
    litellm-cli key create \
      --alias "$KEY_ALIAS" \
      --tier cheap \
      --max-budget "$KEY_MAX_BUDGET" \
      --max-budget-per-day "$KEY_DAILY_BUDGET" \
      || { echo "ABORT: litellm-cli key create failed" >&2; exit 4; }
  fi
else
  echo "skip: litellm-cli not on PATH — defer key mint until LiteLLM up" >&2
fi

# Step 3: Langfuse project tag for the baseline (best-effort; no-op if Langfuse is offline)
if curl -fsS http://localhost:3200/api/public/health >/dev/null 2>&1; then
  echo "todo: Langfuse project tag for $DST (manual via UI; CLI not yet wired)"
else
  echo "skip: Langfuse offline — project tagging deferred to §5.0c bring-up"
fi

# Step 4: validate the cloned dir
if [ -x "$VALIDATE_SCRIPT" ]; then
  echo "validate: $VALIDATE_SCRIPT $DST"
  if "$VALIDATE_SCRIPT" "$DST"; then
    echo "validation: PASS for $DST"
  else
    echo "ABORT: validation failed for $DST" >&2
    exit 3
  fi
else
  echo "skip: $VALIDATE_SCRIPT not executable — not validating"
fi

# Step 5: confirm with profile_dir_contract.py (14/14 expected after this clone)
CONTRACT_TEST="$REPO_ROOT/tests/profile_dir_contract.py"
if [ -f "$CONTRACT_TEST" ]; then
  echo "contract: python3 $CONTRACT_TEST"
  python3 "$CONTRACT_TEST" || {
    echo "WARN: profile_dir_contract.py reported issues — review output" >&2
  }
fi

echo "done: $SRC -> $DST"
