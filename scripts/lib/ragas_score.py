#!/usr/bin/env python3
"""ragas_score.py — Phase 4.7 G1 baseline scorer.

Reads a Promptfoo eval JSON report and emits a single float in [0, 1]
that the capture script writes to the `ragas_score` column.

CONTRACT (per `~/Projects/agents/.planning/phase-4-7-prettyfly-runtime/G1_REFRAME_2026-05-06.md`):
    - --metric answer_relevance: proxy from Promptfoo LLM-rubric pass-rate
    - --metric faithfulness:     proxy from same (RAG-specific Ragas not wired)

This is a v1 proxy implementation. The capture script's contract requires
SOME numeric value that survives the sanity check (0.0 <= ragas <= 1.0).
The proxy uses Promptfoo's existing per-test grader pass-rate, which is
the cleanest available signal that doesn't require a separate Ragas
pipeline. v2 (post-G1) replaces this with the canonical Ragas metric
once the embedding+question-generation pipeline lands.

Usage:
    python3 ragas_score.py --report <promptfoo.json> --metric <name> --model <judge>

Output:
    A single line: "0.7956"  (one float, 4 decimals)
"""

import argparse
import json
import sys
from pathlib import Path


def proxy_score_from_promptfoo(report_path: Path) -> float:
    """Compute proxy answer_relevance from Promptfoo per-test grader scores.

    Promptfoo writes per-test results under `results.results[].gradingResult`,
    which has a `score` field in [0, 1] for llm-rubric assertions. We average
    those scores across all tests.

    If the report has no gradingResult entries (e.g. eval errored out), return
    0.0 — the capture script's sanity check accepts that and the row will show
    a 0.0 baseline that downstream gates can interpret as "eval ran but no
    graded answers."
    """
    try:
        data = json.loads(report_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"# ragas_score: cannot read {report_path}: {exc}", file=sys.stderr)
        return 0.0

    results = data.get("results", {}).get("results", []) or []
    if not results:
        return 0.0

    scores = []
    for r in results:
        grading = r.get("gradingResult") or {}
        primary = grading.get("score")
        if isinstance(primary, (int, float)):
            scores.append(float(primary))
            continue
        # Some Promptfoo configs nest scores under componentResults
        components = grading.get("componentResults") or []
        for c in components:
            s = c.get("score")
            if isinstance(s, (int, float)):
                scores.append(float(s))

    if not scores:
        return 0.0
    return sum(scores) / len(scores)


def main() -> int:
    parser = argparse.ArgumentParser(description="Ragas-proxy scorer for Phase 4.7 G1")
    parser.add_argument("--report", required=True, type=Path, help="Promptfoo JSON report path")
    parser.add_argument("--metric", default="answer_relevance",
                        choices=["answer_relevance", "faithfulness"],
                        help="Metric name (proxy maps both to LLM-rubric pass-rate for v1)")
    parser.add_argument("--model", default="claude-haiku-4-5",
                        help="Judge model (informational only; v1 does not invoke a separate judge)")
    args = parser.parse_args()

    score = proxy_score_from_promptfoo(args.report)
    score = max(0.0, min(1.0, score))  # clamp for sanity-check robustness
    print(f"{score:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
