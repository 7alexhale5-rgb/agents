"""Tests for the priority compute function."""

from __future__ import annotations

from datetime import UTC, datetime

from pf_runtime.communications.priority import compute_priority
from pf_runtime.communications.rules import SiloRules
from pf_runtime.communications.schema import (
    NormalizedMessage,
    Provider,
    TriageBucket,
)


def _msg(
    *,
    sender: str = "stranger@example.com",
    subject: str = "Hello",
    snippet: str = "Hi there",
) -> NormalizedMessage:
    return NormalizedMessage(
        account_id="gmail-1",
        provider=Provider.GOOGLE_MAIL,
        address="alex@example.com",
        folder_or_label="INBOX",
        message_id="m-1",
        thread_id=None,
        sender=sender,
        recipients=(),
        subject=subject,
        received_at=datetime.now(UTC),
        snippet=snippet,
    )


# ---------------------------------------------------------------------------
# P0 — Now
# ---------------------------------------------------------------------------


def test_needs_alex_today_with_urgency_keyword_is_p0() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_ALEX_TODAY,
        msg=_msg(subject="URGENT: contract"),
        silo_rules=SiloRules(),
    )
    assert p == "P0"


def test_needs_alex_today_with_deadline_in_snippet_is_p0() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_ALEX_TODAY,
        msg=_msg(snippet="please respond by EOD"),
        silo_rules=SiloRules(),
    )
    assert p == "P0"


def test_needs_alex_today_from_p0_vip_is_p0() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_ALEX_TODAY,
        msg=_msg(sender="wife@example.com"),
        silo_rules=SiloRules(vips_p0=("wife@example.com",)),
    )
    assert p == "P0"


def test_needs_alex_today_from_billing_sender_is_p0() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_ALEX_TODAY,
        msg=_msg(sender="billing@cloudvendor.com"),
        silo_rules=SiloRules(),
    )
    assert p == "P0"


def test_p0_vip_overrides_bucket() -> None:
    """A P0 VIP escalates regardless of bucket (named-family-tier semantics)."""
    p = compute_priority(
        bucket=TriageBucket.FYI,  # would otherwise be P3
        msg=_msg(sender="wife@example.com"),
        silo_rules=SiloRules(vips_p0=("wife@example.com",)),
    )
    assert p == "P0"


# ---------------------------------------------------------------------------
# P1 — Today
# ---------------------------------------------------------------------------


def test_needs_alex_today_without_urgency_is_p1() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_ALEX_TODAY,
        msg=_msg(subject="Just a check-in"),
        silo_rules=SiloRules(),
    )
    assert p == "P1"


def test_needs_reply_from_any_vip_is_p1() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_REPLY,
        msg=_msg(sender="josh@kohoconsulting.com"),
        silo_rules=SiloRules(vips_any=("*@kohoconsulting.com",)),
    )
    assert p == "P1"


# ---------------------------------------------------------------------------
# P2 — This week
# ---------------------------------------------------------------------------


def test_needs_reply_from_non_vip_is_p2() -> None:
    p = compute_priority(
        bucket=TriageBucket.NEEDS_REPLY,
        msg=_msg(sender="stranger@example.com"),
        silo_rules=SiloRules(),
    )
    assert p == "P2"


def test_schedule_is_p2_by_default() -> None:
    p = compute_priority(
        bucket=TriageBucket.SCHEDULE,
        msg=_msg(),
        silo_rules=SiloRules(),
    )
    assert p == "P2"


def test_release_update_from_vip_is_p2() -> None:
    p = compute_priority(
        bucket=TriageBucket.RELEASE_UPDATE,
        msg=_msg(sender="receipts@stripe.com"),
        silo_rules=SiloRules(vips_any=("receipts@stripe.com",)),
    )
    assert p == "P2"


# ---------------------------------------------------------------------------
# P3 — Background
# ---------------------------------------------------------------------------


def test_promotion_is_p3() -> None:
    p = compute_priority(
        bucket=TriageBucket.PROMOTION,
        msg=_msg(),
        silo_rules=SiloRules(),
    )
    assert p == "P3"


def test_noise_is_p3() -> None:
    p = compute_priority(
        bucket=TriageBucket.NOISE,
        msg=_msg(),
        silo_rules=SiloRules(),
    )
    assert p == "P3"


def test_release_update_non_vip_is_p3() -> None:
    p = compute_priority(
        bucket=TriageBucket.RELEASE_UPDATE,
        msg=_msg(sender="stranger@example.com"),
        silo_rules=SiloRules(),
    )
    assert p == "P3"


def test_fyi_is_p3() -> None:
    assert (
        compute_priority(
            bucket=TriageBucket.FYI, msg=_msg(), silo_rules=SiloRules()
        )
        == "P3"
    )


def test_waiting_is_p3() -> None:
    assert (
        compute_priority(
            bucket=TriageBucket.WAITING, msg=_msg(), silo_rules=SiloRules()
        )
        == "P3"
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_priority_is_deterministic() -> None:
    """Same inputs -> same output. (Smoke test for purity.)"""
    msg = _msg(sender="josh@kohoconsulting.com", subject="Re: Q3 SOW")
    rules = SiloRules(vips_any=("*@kohoconsulting.com",))
    a = compute_priority(bucket=TriageBucket.NEEDS_REPLY, msg=msg, silo_rules=rules)
    b = compute_priority(bucket=TriageBucket.NEEDS_REPLY, msg=msg, silo_rules=rules)
    assert a == b
