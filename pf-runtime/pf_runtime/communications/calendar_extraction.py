"""Calendar metadata extraction from email bodies (Phase 5).

Two deterministic regex-based parsers:

* :func:`extract_meeting_time` — pulls a proposed start time out of the body.
  Recognized patterns (first match wins):

  - HTML ``<time datetime="…">`` attribute (ISO 8601)
  - ICS ``DTSTART:`` lines (UTC ``YYYYMMDDTHHMMSSZ`` and floating local forms)
  - Natural-language ``<weekday> [at] <h[:mm]>am/pm`` ("Tuesday at 2pm")
  - ``tomorrow [at] <time>`` / ``today [at] <time>``
  - ``noon`` keyword as a 12:00 shortcut
  - ``M/D [at] <time>`` short dates ("5/15 at 10am")

  When the body lacks a defensible time reference, returns ``None`` — the
  caller proposes the action without ``proposed_start_iso``. Better to omit
  than to guess wrong.

* :func:`extract_meeting_url` — finds the first Zoom / Teams / Google Meet
  conference URL. Strips trailing sentence punctuation. Returns ``None``
  when no provider URL is present.

Both functions are pure — no I/O, no env, no time-of-day calls outside the
``now`` parameter — so they're trivially testable.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

__all__ = ["extract_meeting_time", "extract_meeting_url"]

# Days of the week → weekday() integer
_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

# `<time datetime="...">` attribute carrying an ISO 8601 string.
_HTML_TIME_RE = re.compile(
    r'<time[^>]+datetime="([^"]+)"',
    re.IGNORECASE,
)

# `DTSTART:20260514T140000Z` (UTC) or `DTSTART:20260514T140000` (floating local).
# We accept the bare form and the timezone-parameter form (DTSTART;TZID=...:...).
_ICS_DTSTART_RE = re.compile(
    r"DTSTART(?:;[^:\n]*)?:(\d{8}T\d{6}Z?)",
    re.IGNORECASE,
)

# "Tuesday at 2pm" / "tuesday 2:30 PM" / "Tue 14:00" — accept the 3-letter
# abbreviations too, but anchor on the long form so "monthly" doesn't match
# via "mon".
_WEEKDAY_TIME_RE = re.compile(
    r"\b(?P<day>"
    r"mon(?:day)?|tue(?:sday)?|wed(?:nesday)?|thu(?:rsday)?|"
    r"fri(?:day)?|sat(?:urday)?|sun(?:day)?"
    r")\b[\s,]*(?:at\s+)?"
    r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)|noon|\d{1,2}:\d{2})",
    re.IGNORECASE,
)


_WEEKDAY_ABBREV: dict[str, str] = {
    "mon": "monday",
    "tue": "tuesday",
    "wed": "wednesday",
    "thu": "thursday",
    "fri": "friday",
    "sat": "saturday",
    "sun": "sunday",
}


def _normalize_weekday(token: str) -> str:
    """Map ``Tue`` / ``tuesday`` (any casing) → the canonical key for ``_WEEKDAYS``."""
    lower = token.lower()
    return _WEEKDAY_ABBREV.get(lower, lower)

# "tomorrow at 3pm" / "today at noon"
_RELATIVE_DAY_TIME_RE = re.compile(
    r"\b(?P<rel>today|tomorrow)\b[\s,]*(?:at\s+)?"
    r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)|noon|\d{1,2}:\d{2})",
    re.IGNORECASE,
)

# "5/15 at 10am" / "5/15 10:00 AM"
_SHORT_DATE_TIME_RE = re.compile(
    r"\b(?P<month>\d{1,2})/(?P<day>\d{1,2})(?:/(?P<year>\d{2,4}))?\b"
    r"[\s,]*(?:at\s+)?"
    r"(?P<time>\d{1,2}(?::\d{2})?\s*(?:am|pm)|noon|\d{1,2}:\d{2})",
    re.IGNORECASE,
)

# Conference URLs. Zoom (us02web | zoom.us), Teams meetup-join, Google Meet.
_MEETING_URL_RE = re.compile(
    r"https?://"
    r"(?:"
    r"(?:[a-z0-9-]+\.)?zoom\.us/j/\d+(?:\?[^\s)<>\"']*)?"
    r"|"
    r"teams\.microsoft\.com/l/meetup-join/[^\s)<>\"']+"
    r"|"
    r"meet\.google\.com/[a-z]+-[a-z]+-[a-z]+(?:\?[^\s)<>\"']*)?"
    r")",
    re.IGNORECASE,
)

# Trailing punctuation we strip from URL captures.
_URL_TRAILING_PUNCT = ".,;:!?)]"


def extract_meeting_time(
    body: str,
    *,
    now: datetime,
    tz: ZoneInfo,
) -> datetime | None:
    """Pull the first defensible meeting time out of ``body``.

    Returns a timezone-aware datetime or ``None`` when nothing matches.
    Resolution order: HTML datetime → ICS DTSTART → short date → weekday →
    relative day. First match wins.

    Args:
        body: Email body text. May contain HTML, plain text, or ICS-fragment
            lines (Gmail sometimes inlines part of the invite payload).
        now: Anchor for relative references ("tomorrow", weekday names).
            Must be timezone-aware.
        tz: Default timezone applied to time references that omit one
            (most natural-language phrases).
    """
    if not body:
        return None

    # 1. HTML <time datetime="..."> — most precise.
    m = _HTML_TIME_RE.search(body)
    if m:
        parsed = _parse_iso8601(m.group(1))
        if parsed is not None:
            return parsed

    # 2. ICS DTSTART.
    m = _ICS_DTSTART_RE.search(body)
    if m:
        parsed = _parse_ics_dtstart(m.group(1))
        if parsed is not None:
            return parsed

    # Normalize `now` to the operator tz once so all branches compare apples
    # to apples — the short-date and weekday paths use it for past-rollover.
    now_local = now.astimezone(tz)

    # 3. Short date "5/15 at 10am". More specific than weekday.
    m = _SHORT_DATE_TIME_RE.search(body)
    if m:
        try:
            month = int(m.group("month"))
            day = int(m.group("day"))
            year_raw = m.group("year")
            year = (
                _two_digit_year_to_full(int(year_raw))
                if year_raw
                else now_local.year
            )
        except ValueError:
            month, day, year = 0, 0, 0
        if 1 <= month <= 12 and 1 <= day <= 31:
            hour, minute = _parse_time_token(m.group("time"))
            if hour is not None:
                target = datetime(year, month, day, hour, minute, tzinfo=tz)
                # If the year wasn't explicit and the date already passed
                # (with a 12-hour grace so "today at 10am, ran at 11am" still
                # reads as today), roll forward to next year.
                if not year_raw and target < now_local - timedelta(hours=12):
                    target = target.replace(year=year + 1)
                return target

    # 4. Weekday + time ("Tuesday at 2pm"). Resolves to next occurrence.
    m = _WEEKDAY_TIME_RE.search(body)
    if m:
        target_weekday = _WEEKDAYS[_normalize_weekday(m.group("day"))]
        hour, minute = _parse_time_token(m.group("time"))
        if hour is not None:
            target = _next_weekday(now, target_weekday, hour, minute, tz)
            return target

    # 5. "tomorrow at 3pm" / "today at noon".
    m = _RELATIVE_DAY_TIME_RE.search(body)
    if m:
        rel = m.group("rel").lower()
        hour, minute = _parse_time_token(m.group("time"))
        if hour is not None:
            target_date = now_local.date()
            if rel == "tomorrow":
                target_date = target_date + timedelta(days=1)
            return datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                hour,
                minute,
                tzinfo=tz,
            )

    return None


def extract_meeting_url(body: str) -> str | None:
    """Return the first Zoom/Teams/Meet conference URL in ``body``, or None.

    Strips trailing sentence punctuation (period, comma, semicolon, etc.) so
    "Use https://meet.google.com/abc-defg-hij." doesn't return a URL with a
    dot suffix.
    """
    if not body:
        return None
    m = _MEETING_URL_RE.search(body)
    if not m:
        return None
    url = m.group(0)
    # Trim trailing punctuation we conservatively treat as not part of the URL.
    while url and url[-1] in _URL_TRAILING_PUNCT:
        url = url[:-1]
    return url


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_time_token(token: str) -> tuple[int | None, int]:
    """Parse "2pm", "2:30 PM", "noon", "14:00" → (hour, minute) or (None, 0)."""
    token = token.strip().lower()
    if token == "noon":  # noqa: S105 - control flow comparison, not a password  # nosec B105
        return 12, 0
    m = re.match(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", token)
    if not m:
        return None, 0
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) else 0
    suffix = m.group(3)
    if suffix == "pm" and hour < 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None, 0
    return hour, minute


def _next_weekday(
    now: datetime,
    target_weekday: int,
    hour: int,
    minute: int,
    tz: ZoneInfo,
) -> datetime:
    """Return the next occurrence of weekday `target_weekday` at hour:minute.

    If today is the target weekday and the requested time is still in the
    future, returns today. Otherwise rolls forward — even when today is the
    target weekday but the time has passed (or is right now), we go to next
    week to avoid scheduling something into the past.
    """
    base = now.astimezone(tz)
    days_ahead = (target_weekday - base.weekday()) % 7
    candidate = datetime(
        base.year, base.month, base.day, hour, minute, tzinfo=tz
    ) + timedelta(days=days_ahead)
    if candidate <= now:
        candidate = candidate + timedelta(days=7)
    return candidate


def _parse_iso8601(value: str) -> datetime | None:
    """Parse an ISO 8601 datetime string. Returns None when unparseable."""
    # Python's fromisoformat handles "+05:00" but not "Z" pre-3.11; we're 3.11+
    # so it does. Normalize trailing Z to +00:00 for older runtimes defensively.
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # Assume UTC for naive — these are wire-format datetimes.
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def _parse_ics_dtstart(value: str) -> datetime | None:
    """Parse an ICS DTSTART value: YYYYMMDDTHHMMSS or YYYYMMDDTHHMMSSZ."""
    candidate = value.strip()
    is_utc = candidate.endswith("Z")
    if is_utc:
        candidate = candidate[:-1]
    if len(candidate) != 15 or candidate[8] != "T":
        return None
    try:
        year = int(candidate[0:4])
        month = int(candidate[4:6])
        day = int(candidate[6:8])
        hour = int(candidate[9:11])
        minute = int(candidate[11:13])
        second = int(candidate[13:15])
    except ValueError:
        return None
    tz = UTC if is_utc else None
    try:
        return datetime(year, month, day, hour, minute, second, tzinfo=tz)
    except ValueError:
        return None


def _two_digit_year_to_full(year: int) -> int:
    """Crude two-digit-year pivot. 00-49 → 2000s, 50-99 → 1900s."""
    if year < 100:
        return 2000 + year if year < 50 else 1900 + year
    return year
