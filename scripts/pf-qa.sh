#!/usr/bin/env bash
# Canonical PF Runtime QA gate: lint, types, tests+coverage, security.
# Expect: cwd can be anything; script cd's into pf-runtime.
# Run from repo root: bash scripts/pf-qa.sh
# With venv active (or uv): dev deps available on PATH.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PF="$ROOT/pf-runtime"

if [[ ! -d "$PF" ]]; then
  echo "error: pf-runtime not found at $PF" >&2
  exit 1
fi

cd "$PF"

if command -v uv >/dev/null 2>&1; then
  _run() { uv run "$@"; }
else
  _run() { "$@"; }
fi

echo "== pf-qa: ruff =="
_run ruff check pf_runtime tests

echo "== pf-qa: mypy =="
_run mypy pf_runtime

echo "== pf-qa: pytest (coverage per pyproject) =="
_run pytest tests/ -q

echo "== pf-qa: bandit =="
_run bandit -c pyproject.toml -r pf_runtime -q

echo "== pf-qa: pip-audit =="
_run pip-audit

echo "pf-qa OK"
