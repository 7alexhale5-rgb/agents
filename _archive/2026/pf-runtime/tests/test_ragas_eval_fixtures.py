"""Repo eval JSON fixtures match ragas_score proxy expectations."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RAGAS = _REPO_ROOT / "scripts" / "lib" / "ragas_score.py"
_SAMPLES = Path(__file__).resolve().parent.parent / "evals" / "personal"


def test_ragas_sample_report_median_score() -> None:
    report = _SAMPLES / "sample-promptfoo-report.json"
    r = subprocess.run(
        [sys.executable, str(_RAGAS), "--report", str(report), "--metric", "answer_relevance"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == "0.8000"


def test_ragas_empty_report_zero() -> None:
    report = _SAMPLES / "empty-promptfoo-report.json"
    r = subprocess.run(
        [sys.executable, str(_RAGAS), "--report", str(report), "--metric", "answer_relevance"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0
    assert r.stdout.strip() == "0.0000"
