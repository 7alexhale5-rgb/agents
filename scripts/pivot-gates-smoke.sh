#!/usr/bin/env bash
# PIVOT §3 gate helpers — verifies scorer CLI + PF preflight (no network).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "== pivot-gates-smoke: wilson lower-CI sample =="
bash scripts/lib/wilson.sh 95 100

echo "== pivot-gates-smoke: ragas_score.py --help =="
python3 scripts/lib/ragas_score.py --help

echo "== pivot-gates-smoke: personal golden sample (promptfoo-shaped JSON) =="
python3 scripts/lib/ragas_score.py \
  --report "$ROOT/pf-runtime/evals/personal/sample-promptfoo-report.json" \
  --metric answer_relevance

echo "== pivot-gates-smoke: pf-cutover-preflight =="
bash scripts/pf-cutover-preflight.sh

echo "pivot-gates-smoke OK"
