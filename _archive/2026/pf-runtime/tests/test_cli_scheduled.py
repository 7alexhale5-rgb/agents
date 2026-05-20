"""Tests for the --scheduled flag's JSON output shape.

The launchd job runs the CLI with --scheduled and pipes stdout to
~/Library/Logs/pf-triage.out. Anything that consumes that log
expects the one-line JSON shape locked here.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from pf_runtime.communications.cli import _format_run_result_json
from pf_runtime.communications.schema import Provider
from pf_runtime.communications.triage_skill import (
    AccountTriageResult,
    TriageRunResult,
)


def _fixture_result(*, with_error: bool = False) -> TriageRunResult:
    started = datetime(2026, 5, 11, 14, 5, 0, tzinfo=UTC)
    finished = started + timedelta(seconds=87)
    accounts = (
        AccountTriageResult(
            account_id="gmail-1",
            provider=Provider.GOOGLE_MAIL,
            fetched=14,
            classified=14,
            proposed=3,
        ),
        AccountTriageResult(
            account_id="koho-m365",
            provider=Provider.MICROSOFT_GRAPH,
            fetched=6,
            classified=6,
            proposed=1,
            error="CredentialExpiredError: expired" if with_error else None,
        ),
    )
    return TriageRunResult(
        run_id="ffff-cycle-id",
        started_at=started,
        finished_at=finished,
        accounts=accounts,
    )


def test_scheduled_json_is_single_line_and_parseable() -> None:
    payload = _format_run_result_json(_fixture_result())
    assert "\n" not in payload
    parsed = json.loads(payload)
    assert parsed["run_id"] == "ffff-cycle-id"
    assert parsed["duration_ms"] == 87_000
    assert parsed["proposals_created"] == 4
    assert parsed["errors"] == 0
    assert len(parsed["accounts"]) == 2


def test_scheduled_json_captures_per_account_error() -> None:
    payload = _format_run_result_json(_fixture_result(with_error=True))
    parsed = json.loads(payload)
    assert parsed["errors"] == 1
    bad = next(a for a in parsed["accounts"] if a["account_id"] == "koho-m365")
    assert bad["error"] == "CredentialExpiredError: expired"
    good = next(a for a in parsed["accounts"] if a["account_id"] == "gmail-1")
    assert good["error"] is None


def test_scheduled_json_uses_compact_separators_for_log_friendliness() -> None:
    payload = _format_run_result_json(_fixture_result())
    # No spaces after commas/colons — keeps each cycle log line short
    # enough that `tail -f` and grep are usable in a regular terminal.
    assert ", " not in payload
    assert ": " not in payload
