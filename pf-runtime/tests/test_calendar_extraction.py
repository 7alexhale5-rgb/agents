"""Calendar-extraction unit tests (Phase 5).

`extract_meeting_time` parses natural-language and structured time references
from email bodies. `extract_meeting_url` finds Zoom/Teams/Meet conference URLs.
Both are deterministic regex-based parsers — when the body is ambiguous,
they return None and the caller proceeds without that field.
"""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from pf_runtime.communications.calendar_extraction import (
    extract_meeting_time,
    extract_meeting_url,
)

# Anchor "now" for relative-time tests: Monday 2026-05-11 10:00 CT.
_NOW = datetime(2026, 5, 11, 10, 0, 0, tzinfo=ZoneInfo("America/Chicago"))
_CT = ZoneInfo("America/Chicago")


# ---------------------------------------------------------------------------
# extract_meeting_time
# ---------------------------------------------------------------------------


def test_weekday_with_time_resolves_to_next_occurrence() -> None:
    body = "Can we sync Tuesday at 2pm?"
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.weekday() == 1  # Tuesday
    assert result.hour == 14
    assert result.minute == 0
    assert result.tzinfo is not None


def test_tomorrow_at_time() -> None:
    body = "How about tomorrow at 3pm CT?"
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.day == 12  # _NOW is May 11, tomorrow is May 12
    assert result.hour == 15


def test_explicit_date_with_time() -> None:
    body = "Let's meet on 5/15 at 10am."
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.month == 5
    assert result.day == 15
    assert result.hour == 10


def test_noon_keyword() -> None:
    body = "Tuesday at noon works for me."
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.weekday() == 1
    assert result.hour == 12


def test_html_time_datetime_attribute() -> None:
    body = (
        'Confirmed: <time datetime="2026-05-13T15:30:00-05:00">Wed 3:30pm CT</time>'
    )
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 13
    assert result.hour == 15
    assert result.minute == 30


def test_ics_dtstart_inline() -> None:
    body = "Meeting invite:\nDTSTART:20260514T140000Z\nDTEND:20260514T150000Z"
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.year == 2026
    assert result.month == 5
    assert result.day == 14
    # ICS UTC time → 14:00Z is 9am CT
    assert result.astimezone(UTC).hour == 14


def test_no_time_in_body_returns_none() -> None:
    body = "Hey, just wanted to share thoughts on the proposal. No urgency."
    assert extract_meeting_time(body, now=_NOW, tz=_CT) is None


def test_ambiguous_time_only_returns_none() -> None:
    # Bare "2pm" without a day reference is genuinely ambiguous — punt.
    body = "Will get this to you by 2pm."
    assert extract_meeting_time(body, now=_NOW, tz=_CT) is None


def test_past_weekday_resolves_to_next_week() -> None:
    # _NOW is Monday. "Monday 9am" should resolve to NEXT Monday, not today.
    body = "Monday at 9am?"
    result = extract_meeting_time(body, now=_NOW, tz=_CT)
    assert result is not None
    assert result.weekday() == 0
    assert result.day == 18  # Next Monday is May 18


# ---------------------------------------------------------------------------
# extract_meeting_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "body, expected_substr",
    [
        ("Join: https://us02web.zoom.us/j/12345678901", "zoom.us/j/12345678901"),
        ("https://zoom.us/j/987654321?pwd=abc123", "zoom.us/j/987654321"),
        (
            "Teams: https://teams.microsoft.com/l/meetup-join/19%3ameeting_abc/0?context=...",
            "teams.microsoft.com/l/meetup-join",
        ),
        ("Meet me: https://meet.google.com/abc-defg-hij", "meet.google.com/abc-defg-hij"),
    ],
)
def test_extract_meeting_url_finds_provider(body: str, expected_substr: str) -> None:
    result = extract_meeting_url(body)
    assert result is not None
    assert expected_substr in result


def test_no_meeting_url_returns_none() -> None:
    body = "Let's chat Tuesday 2pm. I'll send a calendar invite."
    assert extract_meeting_url(body) is None


def test_meeting_url_strips_trailing_punctuation() -> None:
    body = "Use this link: https://meet.google.com/abc-defg-hij."
    result = extract_meeting_url(body)
    assert result is not None
    assert not result.endswith(".")


def test_first_url_wins_on_multiple() -> None:
    body = (
        "Backup zoom: https://zoom.us/j/111 — primary "
        "https://meet.google.com/abc-defg-hij"
    )
    result = extract_meeting_url(body)
    assert result is not None
    # First match wins.
    assert "zoom.us/j/111" in result
