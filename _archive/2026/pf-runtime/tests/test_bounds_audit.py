"""BoundsAuditor SQLite counters."""
from __future__ import annotations

from pathlib import Path

from pf_runtime.dream.bounds_audit import AuditResult, BoundsAuditor


def test_skill_cap_72h(tmp_path: Path) -> None:
    home = tmp_path / "hermes"
    b = BoundsAuditor("personal", home)
    assert b.check_new_skill_allowed(max_per_72h=3) == AuditResult.APPROVED
    b.record_skill_created()
    b.record_skill_created()
    b.record_skill_created()
    assert b.check_new_skill_allowed(max_per_72h=3) == AuditResult.HALT_PROFILE


def test_episodic_daily_cap(tmp_path: Path) -> None:
    home = tmp_path / "hermes"
    b = BoundsAuditor("personal", home)
    assert b.check_episodic_write_allowed(max_per_day=2) == AuditResult.APPROVED
    b.record_episodic_write()
    b.record_episodic_write()
    assert b.check_episodic_write_allowed(max_per_day=2) == (
        AuditResult.HALT_PROFILE_FOR_TODAY
    )
