"""SqliteInboundLedger dedup."""
from __future__ import annotations

from pathlib import Path

from pf_runtime.runtime.inbound_ledger import SqliteInboundLedger


def test_try_claim_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "dedup.sqlite"
    led = SqliteInboundLedger(db)
    assert led.try_claim("evt-1") is True
    assert led.try_claim("evt-1") is False
    assert led.try_claim("evt-2") is True


def test_empty_key_always_claims(tmp_path: Path) -> None:
    led = SqliteInboundLedger(tmp_path / "x.sqlite")
    assert led.try_claim("") is True


def test_outbound_round_trip(tmp_path: Path) -> None:
    led = SqliteInboundLedger(tmp_path / "dedup.sqlite")
    assert led.outbound_already_sent("p:evt-a") is False
    led.record_outbound_sent("p:evt-a")
    assert led.outbound_already_sent("p:evt-a") is True


def test_outbound_empty_key_is_noop(tmp_path: Path) -> None:
    led = SqliteInboundLedger(tmp_path / "d.sqlite")
    led.record_outbound_sent("")
    assert led.outbound_already_sent("") is False
