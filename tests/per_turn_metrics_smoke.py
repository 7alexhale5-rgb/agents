#!/usr/bin/env python3
"""Smoke test for scripts/lib/per_turn_metrics.py.

Builds an in-memory SQLite fixture matching Hermes's `messages` and
`sessions` schema, exercises three scenarios, and asserts the TSV output
shape + numeric properties.

Run: python3 tests/per_turn_metrics_smoke.py
Exit: 0 = all asserts pass; 1 = any failure.
"""

import importlib.util
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Anchor fixture timestamps to the target date so the SQLite query
# `date(timestamp, 'unixepoch') = ?` actually matches.
TARGET_DATE = "2026-05-03"
DAY_START_EPOCH = datetime.fromisoformat(TARGET_DATE + "T00:00:00+00:00").timestamp()

REPO_ROOT = Path(__file__).resolve().parent.parent
HELPER_PATH = REPO_ROOT / "scripts" / "lib" / "per_turn_metrics.py"

spec = importlib.util.spec_from_file_location("per_turn_metrics", HELPER_PATH)
ptm = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ptm)


def make_fixture_db(tmp_path: Path, scenario: str) -> str:
    db = tmp_path / f"{scenario}.db"
    con = sqlite3.connect(db)
    con.executescript(
        """
        CREATE TABLE sessions (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            started_at REAL NOT NULL,
            ended_at REAL,
            estimated_cost_usd REAL DEFAULT 0
        );
        CREATE TABLE messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            timestamp REAL NOT NULL
        );
        """
    )

    if scenario == "empty":
        pass

    elif scenario == "single_turn":
        # 1 session, 1 user → 1 assistant pair, 5s latency, $0.04 session cost
        # Anchor at noon UTC of the target date.
        base = DAY_START_EPOCH + 12 * 3600
        con.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            ("s1", "slack", base, base + 10, 0.04),
        )
        con.execute(
            "INSERT INTO messages (session_id, role, timestamp) VALUES (?, ?, ?)",
            ("s1", "user", base),
        )
        con.execute(
            "INSERT INTO messages (session_id, role, timestamp) VALUES (?, ?, ?)",
            ("s1", "assistant", base + 5),
        )

    elif scenario == "multi_turn":
        # 2 sessions, total 5 user turns. Costs distributed:
        #   s1: 3 user turns × $0.10 session → $0.0333 each
        #   s2: 2 user turns × $0.20 session → $0.10 each
        s1_base = DAY_START_EPOCH + 10 * 3600
        s2_base = DAY_START_EPOCH + 14 * 3600
        con.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            ("s1", "slack", s1_base, s1_base + 100, 0.10),
        )
        con.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            ("s2", "slack", s2_base, s2_base + 100, 0.20),
        )
        # s1: user → assistant pairs at offsets, latencies 2s / 4s / 10s
        for role, off in [
            ("user", 1), ("assistant", 3),
            ("user", 20), ("assistant", 24),
            ("user", 50), ("assistant", 60),
        ]:
            con.execute(
                "INSERT INTO messages (session_id, role, timestamp) VALUES (?, ?, ?)",
                ("s1", role, s1_base + off),
            )
        # s2: user → assistant pairs, latencies 3s / 6s
        for role, off in [
            ("user", 5), ("assistant", 8),
            ("user", 30), ("assistant", 36),
        ]:
            con.execute(
                "INSERT INTO messages (session_id, role, timestamp) VALUES (?, ?, ?)",
                ("s2", role, s2_base + off),
            )

    con.commit()
    con.close()
    return str(db)


def run_scenario(db_path: str, target_date: str):
    """Bypass langfuse + cli; call the helper functions directly."""
    turns = ptm.pull_turns_from_messages(db_path, target_date, source="slack")
    latencies = [asst - usr for _, usr, asst, _ in turns]
    costs = ptm.cost_per_turn_heuristic(turns)
    latencies = [max(0.0, v) for v in latencies]
    costs = [max(0.0, v) for v in costs]
    return ptm.emit_tsv(len(turns), costs, latencies), turns, costs, latencies


def fail(name: str, msg: str):
    print(f"FAIL: {name} — {msg}")
    return 1


def main() -> int:
    failed = 0
    passed = 0
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        target = TARGET_DATE

        # --- Scenario 1: empty DB → zeros, valid TSV shape ---
        db = make_fixture_db(tmp_path, "empty")
        tsv, turns, costs, latencies = run_scenario(db, target)
        cols = tsv.split("\t")
        if len(cols) != 9:
            failed += fail("empty: 9 columns", f"got {len(cols)}")
        else:
            passed += 1
        if cols and cols[0] != "0":
            failed += fail("empty: n_turns=0", f"got {cols[0]}")
        else:
            passed += 1

        # --- Scenario 2: single turn → all metrics single-valued, CI=point ---
        db = make_fixture_db(tmp_path, "single_turn")
        tsv, turns, costs, latencies = run_scenario(db, target)
        cols = tsv.split("\t")
        if cols[0] != "1":
            failed += fail("single_turn: n_turns=1", f"got {cols[0]}")
        else:
            passed += 1
        # latency = 5s exact (asst 1714700005 - user 1714700000)
        if abs(float(cols[5]) - 5.0) > 0.001:
            failed += fail("single_turn: p50_lat=5", f"got {cols[5]}")
        else:
            passed += 1
        # cost: 0.04 / 1 user msg = 0.04 per turn
        if abs(float(cols[1]) - 0.04) > 0.0001:
            failed += fail("single_turn: p50_cost=0.04", f"got {cols[1]}")
        else:
            passed += 1
        # N=1 → CI bounds collapse to point estimate
        if cols[3] != cols[4]:
            failed += fail("single_turn: cost CI collapsed", f"low={cols[3]} high={cols[4]}")
        else:
            passed += 1

        # --- Scenario 3: multi-turn distribution → percentiles + CI ---
        db = make_fixture_db(tmp_path, "multi_turn")
        tsv, turns, costs, latencies = run_scenario(db, target)
        cols = tsv.split("\t")
        if cols[0] != "5":
            failed += fail("multi_turn: n_turns=5", f"got {cols[0]}")
        else:
            passed += 1
        # Latency vector: [2, 4, 10, 3, 6] sorted = [2, 3, 4, 6, 10]
        # p50 ≈ 4, p95 ≈ 10
        if abs(float(cols[5]) - 4.0) > 0.001:
            failed += fail("multi_turn: p50_lat≈4", f"got {cols[5]}")
        else:
            passed += 1
        if abs(float(cols[6]) - 10.0) > 0.001:
            failed += fail("multi_turn: p95_lat=10", f"got {cols[6]}")
        else:
            passed += 1
        # Cost vector heuristic: s1 has 3 turns × $0.10 / 3 = $0.0333 each;
        # s2 has 2 turns × $0.20 / 2 = $0.10 each. Sorted: [.0333, .0333, .0333, .10, .10]
        # p50 ≈ 0.0333
        if abs(float(cols[1]) - 0.0333) > 0.0005:
            failed += fail("multi_turn: p50_cost≈0.0333", f"got {cols[1]}")
        else:
            passed += 1
        # CI bounds on cost p50: [low, high] should bracket the point estimate
        ci_low_c = float(cols[3])
        ci_high_c = float(cols[4])
        p50_c = float(cols[1])
        if not (ci_low_c <= p50_c <= ci_high_c):
            failed += fail(
                "multi_turn: cost CI brackets p50",
                f"low={ci_low_c} p50={p50_c} high={ci_high_c}",
            )
        else:
            passed += 1

    print(f"\nper_turn_metrics smoke: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
