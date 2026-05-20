"""Classifier regression gate for the inbox triage stack.

Runs the production classifier prompt against a hand-labeled fixture
of email threads and fails if bucket-match accuracy drops below 85%.
Any PR that changes ``triage_skill.py``, the classifier prompt, or
``DEFAULT_CLASSIFIER_MODEL`` should run this and stay green.

By default this test is **skipped** because it would hit the real
OpenRouter API on every CI run. To run it locally:

    PFRT_REGRESSION_LIVE=1 PFRT_OPENROUTER_KEY=... \\
        pytest pf-runtime/tests/test_classifier_regression.py -v

The fixture starts at 10 synthetic threads covering all 8 buckets
(see fixtures/classifier_regression.jsonl). The Phase 3 plan calls
for expanding to 50 hand-labeled threads from Alex's real inboxes
before flipping the classifier default in production-critical paths;
the 10-thread starter set protects against gross regressions today.

TODO(operator): expand fixture to 50 threads with the following mix:
    - 8 NEEDS_ALEX_TODAY (urgent named asks / deadlines / billing)
    - 12 NEEDS_REPLY (direct questions from named contacts)
    - 6 SCHEDULE (meeting requests, calendar holds)
    - 6 PROMOTION (marketing with unsubscribe footer)
    - 4 RELEASE_UPDATE (transactional digests, version notes)
    - 4 NOISE (newsletters, social digests)
    - 6 FYI (status updates, OOO replies)
    - 4 WAITING (pending-update threads)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    REPO_ROOT / "pf-runtime" / "tests" / "fixtures" / "classifier_regression.jsonl"
)

# Single source of truth for the regression gate; raising this number
# without expanding the fixture should be impossible.
ACCURACY_GATE = 0.85


def _load_fixture() -> list[dict[str, str]]:
    with FIXTURE_PATH.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def test_regression_fixture_is_well_formed() -> None:
    """Pre-flight: ensures every fixture row has the columns the live
    test reads. Always runs in CI so a malformed JSONL surfaces before
    anyone tries to flip the gate."""
    rows = _load_fixture()
    assert len(rows) >= 5, "fixture must have at least 5 rows"
    required = {"thread_id", "subject", "from", "snippet", "expected_bucket"}
    for row in rows:
        missing = required - row.keys()
        assert not missing, f"{row.get('thread_id', '?')} missing fields: {missing}"
        assert row["expected_bucket"] in {
            "needs_alex_today",
            "needs_reply",
            "schedule",
            "waiting",
            "fyi",
            "promotion",
            "release_update",
            "noise",
        }, f"unknown bucket {row['expected_bucket']!r} in {row['thread_id']}"


def test_regression_thread_ids_are_unique() -> None:
    rows = _load_fixture()
    ids = [r["thread_id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate thread_id in fixture"


@pytest.mark.skipif(
    os.environ.get("PFRT_REGRESSION_LIVE") != "1",
    reason="Live OpenRouter call gated on PFRT_REGRESSION_LIVE=1",
)
def test_classifier_regression_passes_gate() -> None:
    """Run the classifier against the fixture and assert >= 85% match.

    Skipped by default — running on every CI hit would burn a real
    OpenRouter call per fixture row. Run locally before merging any
    PR that touches triage_skill.py or the model default.
    """
    pytest.importorskip("pf_runtime.runtime.model_adapter")
    import asyncio
    from datetime import UTC, datetime

    from pf_runtime.communications.cli import DEFAULT_CLASSIFIER_MODEL
    from pf_runtime.communications.schema import (
        NormalizedMessage,
        Provider,
    )
    from pf_runtime.communications.triage_skill import _classify_batch
    from pf_runtime.runtime.model_adapter import OpenRouterAdapter

    rows = _load_fixture()
    messages = [
        NormalizedMessage(
            account_id="regression",
            provider=Provider.GOOGLE_MAIL,
            address="alex@prettyflyforai.com",
            folder_or_label="INBOX",
            message_id=row["thread_id"],
            thread_id=None,
            sender=row["from"],
            recipients=(),
            subject=row["subject"],
            received_at=datetime.now(UTC),
            snippet=row["snippet"],
        )
        for row in rows
    ]

    # OpenRouterAdapter reads the API key from .env at the configured
    # path; the integration test runs against the real model.
    adapter = OpenRouterAdapter(env_path=None)
    classifications = asyncio.run(
        _classify_batch(
            adapter=adapter,
            model=DEFAULT_CLASSIFIER_MODEL,
            messages=messages,
        )
    )

    matches = sum(
        1
        for expected_row, got in zip(rows, classifications, strict=True)
        if got.bucket.value == expected_row["expected_bucket"]
    )
    accuracy = matches / len(rows)
    assert accuracy >= ACCURACY_GATE, (
        f"classifier {DEFAULT_CLASSIFIER_MODEL} matched {matches}/{len(rows)} "
        f"= {accuracy:.0%}; gate is {ACCURACY_GATE:.0%}"
    )
