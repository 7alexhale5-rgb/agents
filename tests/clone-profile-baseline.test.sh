#!/usr/bin/env bash
# clone-profile-baseline.test.sh — sanity test for scripts/clone-profile-baseline.sh
#
# What this asserts (no real LiteLLM/Langfuse calls; those are deferred manual steps):
#   1. Script rejects missing args
#   2. Script rejects non-kebab-case target names
#   3. Re-running over existing personal-baseline is a no-op (idempotency)
#   4. Target manifest.json sku matches target name after run
#
# Run: bash tests/clone-profile-baseline.test.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/clone-profile-baseline.sh"
FAILS=0

assert_exit () {
  local label="$1" expected="$2"; shift 2
  set +e
  "$@" >/dev/null 2>&1
  local got=$?
  set -e
  if [ "$got" -eq "$expected" ]; then
    echo "PASS  $label (exit $got)"
  else
    echo "FAIL  $label (expected exit $expected, got $got)"
    FAILS=$((FAILS+1))
  fi
}

# 1. Missing args
assert_exit "missing args"        1 "$SCRIPT"
assert_exit "missing target arg"  1 "$SCRIPT" personal

# 2. Bad target name
assert_exit "bad name (uppercase)" 2 "$SCRIPT" personal Personal-Baseline
assert_exit "bad name (underscore)" 2 "$SCRIPT" personal personal_baseline

# 3. Idempotency: re-running over existing baseline should succeed (exit 0)
#    Requires personal-baseline runtime dir to exist (it does, per §5.1 manual run).
if [ -d "$HOME/.hermes/profiles/personal-baseline" ]; then
  assert_exit "idempotent re-run" 0 "$SCRIPT" personal personal-baseline
else
  echo "SKIP  idempotent re-run (no personal-baseline runtime dir to test against)"
fi

# 4. Post-run: target manifest.json sku must equal target name
RUNTIME_MANIFEST="$HOME/.hermes/profiles/personal-baseline/manifest.json"
if [ -f "$RUNTIME_MANIFEST" ]; then
  ACTUAL_SKU=$(python3 -c "import json; print(json.load(open('$RUNTIME_MANIFEST'))['sku'])")
  if [ "$ACTUAL_SKU" = "personal-baseline" ]; then
    echo "PASS  runtime manifest sku == personal-baseline"
  else
    echo "FAIL  runtime manifest sku == personal-baseline (got: $ACTUAL_SKU)"
    FAILS=$((FAILS+1))
  fi
fi

echo ""
if [ "$FAILS" -eq 0 ]; then
  echo "ALL TESTS PASSED"
  exit 0
else
  echo "$FAILS TEST(S) FAILED"
  exit 1
fi
