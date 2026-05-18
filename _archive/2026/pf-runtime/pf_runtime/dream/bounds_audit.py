"""Skill self-gen bounds — SQLite counters per profile (SKILL_SELF_GEN_BOUNDS.md)."""
from __future__ import annotations

import sqlite3
import time
from enum import StrEnum
from pathlib import Path


class AuditResult(StrEnum):
    """Gate outcome before persisting a new skill or episodic write."""

    APPROVED = "approved"
    REJECT_TOO_LARGE = "reject_too_large"
    HALT_PROFILE = "halt_profile"
    HALT_PROFILE_FOR_TODAY = "halt_profile_for_today"


class BoundsAuditor:
    """Tracks per-profile limits: new skills in 72h, episodic writes per day."""

    def __init__(self, profile_slug: str, hermes_home: Path) -> None:
        if not profile_slug:
            raise ValueError("profile_slug required")
        self.profile_slug = profile_slug
        self._db_path = (
            hermes_home.expanduser().resolve()
            / "profiles"
            / profile_slug
            / "runtime-state"
            / "bounds.sqlite"
        )
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS skill_created (
                    ts REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episodic_write (
                    day TEXT NOT NULL,
                    count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (day)
                )
                """
            )
            conn.commit()

    def count_new_skills_72h(self) -> int:
        cutoff = time.time() - 72 * 3600
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM skill_created WHERE ts >= ?",
                (cutoff,),
            ).fetchone()
        return int(row[0]) if row else 0

    def record_skill_created(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("INSERT INTO skill_created (ts) VALUES (?)", (time.time(),))
            conn.commit()

    def check_new_skill_allowed(self, *, max_per_72h: int = 3) -> AuditResult:
        if self.count_new_skills_72h() >= max_per_72h:
            return AuditResult.HALT_PROFILE
        return AuditResult.APPROVED

    def episodic_writes_for_day(self, day_iso: str | None = None) -> int:
        if day_iso is None:
            day_iso = time.strftime("%Y-%m-%d", time.gmtime())
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT count FROM episodic_write WHERE day = ?",
                (day_iso,),
            ).fetchone()
        return int(row[0]) if row else 0

    def record_episodic_write(self) -> None:
        day_iso = time.strftime("%Y-%m-%d", time.gmtime())
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO episodic_write (day, count) VALUES (?, 1)
                ON CONFLICT(day) DO UPDATE SET count = count + 1
                """,
                (day_iso,),
            )
            conn.commit()

    def check_episodic_write_allowed(self, *, max_per_day: int = 50) -> AuditResult:
        if self.episodic_writes_for_day() >= max_per_day:
            return AuditResult.HALT_PROFILE_FOR_TODAY
        return AuditResult.APPROVED
