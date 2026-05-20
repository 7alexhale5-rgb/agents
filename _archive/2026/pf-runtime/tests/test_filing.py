"""Tests for the filing label suggester."""

from __future__ import annotations

from datetime import UTC, datetime

from pf_runtime.communications.filing import suggest_label
from pf_runtime.communications.rules import RoleHint, SiloRules
from pf_runtime.communications.schema import (
    NormalizedMessage,
    Provider,
    TriageBucket,
)


def _msg(*, sender: str = "stranger@example.com") -> NormalizedMessage:
    return NormalizedMessage(
        account_id="gmail-1",
        provider=Provider.GOOGLE_MAIL,
        address="alex@example.com",
        folder_or_label="INBOX",
        message_id="m-1",
        thread_id=None,
        sender=sender,
        recipients=(),
        subject="Hi",
        received_at=datetime.now(UTC),
        snippet="hello",
    )


def test_role_hint_match_wins_over_bucket_default() -> None:
    rules = SiloRules(
        role_hints=(RoleHint(pattern="*@kohoconsulting.com", label_suffix="Internal"),)
    )
    label = suggest_label(
        silo="koho",
        bucket=TriageBucket.PROMOTION,  # would default to Newsletters
        msg=_msg(sender="josh@kohoconsulting.com"),
        silo_rules=rules,
    )
    assert label == "KOHO/Internal"


def test_specific_pattern_first_wins() -> None:
    rules = SiloRules(
        role_hints=(
            RoleHint(pattern="josh@kohoconsulting.com", label_suffix="Clients/Josh"),
            RoleHint(pattern="*@kohoconsulting.com", label_suffix="Internal"),
        )
    )
    assert (
        suggest_label(
            silo="koho",
            bucket=TriageBucket.NEEDS_REPLY,
            msg=_msg(sender="josh@kohoconsulting.com"),
            silo_rules=rules,
        )
        == "KOHO/Clients/Josh"
    )


def test_promotion_falls_back_to_newsletters() -> None:
    assert (
        suggest_label(
            silo="prettyfly",
            bucket=TriageBucket.PROMOTION,
            msg=_msg(),
            silo_rules=SiloRules(),
        )
        == "PF/Newsletters"
    )


def test_noise_falls_back_to_archive() -> None:
    assert (
        suggest_label(
            silo="ctox",
            bucket=TriageBucket.NOISE,
            msg=_msg(),
            silo_rules=SiloRules(),
        )
        == "CTOX/Archive"
    )


def test_needs_reply_with_no_hint_returns_none() -> None:
    """NEEDS_REPLY has no bucket-default; without a role_hint match, no
    label is suggested. The card still shows the bucket badge."""
    assert (
        suggest_label(
            silo="koho",
            bucket=TriageBucket.NEEDS_REPLY,
            msg=_msg(sender="stranger@example.com"),
            silo_rules=SiloRules(),
        )
        is None
    )


def test_unknown_silo_returns_none() -> None:
    """Writeback slugs without a triage prefix (home/fleet/skills/ops/rnd)
    never produce a suggestion."""
    assert (
        suggest_label(
            silo="home",
            bucket=TriageBucket.NEEDS_REPLY,
            msg=_msg(),
            silo_rules=SiloRules(),
        )
        is None
    )


def test_all_four_silos_get_their_prefix() -> None:
    rules = SiloRules(
        role_hints=(RoleHint(pattern="*@*", label_suffix="Custom"),)
    )
    for silo, expected_prefix in [
        ("koho", "KOHO"),
        ("ctox", "CTOX"),
        ("yeh", "YEH"),
        ("prettyfly", "PF"),
    ]:
        label = suggest_label(
            silo=silo,
            bucket=TriageBucket.NEEDS_REPLY,
            msg=_msg(sender="anyone@example.com"),
            silo_rules=rules,
        )
        assert label == f"{expected_prefix}/Custom"


def test_fyi_falls_back_to_reference() -> None:
    assert (
        suggest_label(
            silo="koho",
            bucket=TriageBucket.FYI,
            msg=_msg(),
            silo_rules=SiloRules(),
        )
        == "KOHO/Reference"
    )


def test_waiting_falls_back_to_waiting() -> None:
    assert (
        suggest_label(
            silo="koho",
            bucket=TriageBucket.WAITING,
            msg=_msg(),
            silo_rules=SiloRules(),
        )
        == "KOHO/Waiting"
    )
