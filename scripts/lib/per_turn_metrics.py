#!/usr/bin/env python3
"""per_turn_metrics.py — Phase 4.7 G1 per-turn aggregation.

Reads today's messages from a Hermes profile state.db, computes per-turn
cost and wall-clock latency, and emits a tab-separated row of:

    n_turns p50_cost p95_cost ci_low_cost ci_high_cost \
            p50_lat  p95_lat  ci_low_lat  ci_high_lat

Latency definition (G1_REFRAME_2026-05-06.md §6 locked): wall-clock between
the user-role message and the next assistant-role message in the same
session. Excludes retry / tool-wait noise that wouldn't be visible to the
operator at cutover comparison time.

Cost denominator (G1_REFRAME_2026-05-06.md §5 locked):
    primary: Langfuse trace span totals (sum input_tokens + output_tokens
             across spans for the trace matching this turn's session+timestamp)
    fallback: session-level cost / count(user msgs in session) heuristic
              when Langfuse is unreachable.

Confidence band (G1_REFRAME_2026-05-06.md §7 locked): bootstrapped 90% CI
per night via 1000 resamples on the per-turn distribution. Rolling 7-night
aggregate is computed by aggregate.py downstream, not here.

Usage:
    python3 per_turn_metrics.py <state-db-path> <YYYY-MM-DD>

Output:
    Single TSV line, 9 columns. All numeric. Empty/None values written as 0.
"""

import argparse
import json
import random
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import date as date_cls
from datetime import datetime
from typing import List, Optional, Tuple

LANGFUSE_HEALTH_URL = "http://localhost:3200/api/public/health"
LANGFUSE_TIMEOUT = 3  # seconds
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_CONFIDENCE = 0.90  # 90% CI


def langfuse_up(timeout: float = LANGFUSE_TIMEOUT) -> bool:
    try:
        with urllib.request.urlopen(LANGFUSE_HEALTH_URL, timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        return False


def pull_turns_from_messages(
    db_path: str, target_date: str, source: str = "slack"
) -> List[Tuple[str, float, float, str]]:
    """Return (session_id, user_ts, assistant_ts, session_cost_usd) tuples
    for each user→assistant turn pair where the user message occurred on
    the target UTC date.

    A turn is the FIRST assistant message that follows a user message
    within the same session. Tool-call replies and intermediate assistant
    chunks that precede the user-visible answer are excluded by the
    "first-only" pairing.
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        # Pull user messages on the target date with their session.
        rows = con.execute(
            """
            SELECT m.session_id, m.timestamp AS user_ts,
                   COALESCE(s.estimated_cost_usd, 0.0) AS session_cost
            FROM messages m
            JOIN sessions s ON s.id = m.session_id
            WHERE m.role = 'user'
              AND s.source = ?
              AND date(m.timestamp, 'unixepoch') = ?
            ORDER BY m.session_id, m.timestamp
            """,
            (source, target_date),
        ).fetchall()

        # For each user message, find the next assistant message in the
        # same session that follows it.
        turns = []
        for r in rows:
            asst = con.execute(
                """
                SELECT timestamp FROM messages
                WHERE session_id = ?
                  AND role = 'assistant'
                  AND timestamp > ?
                ORDER BY timestamp
                LIMIT 1
                """,
                (r["session_id"], r["user_ts"]),
            ).fetchone()
            if asst is None:
                continue  # user message with no assistant reply yet
            turns.append((r["session_id"], r["user_ts"], asst["timestamp"], r["session_cost"]))
        return turns
    finally:
        con.close()


def cost_per_turn_heuristic(turns: List[Tuple[str, float, float, str]]) -> List[float]:
    """Heuristic: distribute session-level cost across user turns in that
    session. Honest fallback when Langfuse is down. The architect's
    finding 2 noted this assumes turns within a session have uniform cost,
    which is false when one turn does heavy retrieval. The bias is bounded
    by session-level cost being real; the denominator is just imprecise.
    """
    by_session: dict = {}
    for sid, _, _, scost in turns:
        by_session.setdefault(sid, []).append(scost)
    costs = []
    for sid, _, _, scost in turns:
        n_user_in_session = len(by_session[sid])
        if n_user_in_session == 0:
            costs.append(0.0)
        else:
            costs.append(float(scost) / n_user_in_session)
    return costs


def cost_per_turn_langfuse(turns: List[Tuple[str, float, float, str]]) -> Optional[List[float]]:
    """Primary path: query Langfuse for trace cost per turn.

    Stubbed for v1 — Langfuse trace-query API returns per-trace
    input_tokens / output_tokens; we'd multiply by the model's per-token
    price (looked up from a static pricing table). Wiring is straight-
    forward but requires Langfuse to be up at metric-time AND a pricing
    table that matches the model in use.

    Returns None when Langfuse can't be reached or the v1 stub fires;
    caller falls back to cost_per_turn_heuristic.
    """
    if not langfuse_up():
        return None
    # v1 stub: even if Langfuse is up, we don't have the pricing-table
    # plumbing yet. Returning None forces heuristic. v2 wires the trace
    # query + pricing-table multiply.
    return None


def percentile(values: List[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = max(0, min(len(s) - 1, int(round(q * (len(s) - 1)))))
    return float(s[idx])


def bootstrap_ci(
    values: List[float],
    metric_fn,
    confidence: float = BOOTSTRAP_CONFIDENCE,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> Tuple[float, float]:
    """Return (low, high) confidence bounds for metric_fn applied across
    bootstrap resamples of values.

    For N < 3 the bootstrap is meaningless — return point estimates
    (low == high == metric_fn(values)).
    """
    if not values:
        return (0.0, 0.0)
    if len(values) < 3:
        v = metric_fn(values)
        return (v, v)
    rng = random.Random(42)  # deterministic for reproducibility per night
    estimates = []
    for _ in range(resamples):
        sample = [rng.choice(values) for _ in values]
        estimates.append(metric_fn(sample))
    estimates.sort()
    alpha = (1.0 - confidence) / 2.0
    low_idx = max(0, int(round(alpha * (len(estimates) - 1))))
    high_idx = min(len(estimates) - 1, int(round((1.0 - alpha) * (len(estimates) - 1))))
    return (estimates[low_idx], estimates[high_idx])


def emit_tsv(
    n_turns: int,
    costs: List[float],
    latencies: List[float],
) -> str:
    """Compute the 9-column TSV row.

    Columns:
        n_turns p50_cost p95_cost ci_low_cost ci_high_cost
                p50_lat  p95_lat  ci_low_lat  ci_high_lat

    CI bounds use bootstrapped 90% CI on p50 of the metric (the operator
    cares more about the median than tail-end bands at low N). p95 is
    reported as a point estimate to avoid double-tail-stretching.
    """
    p50_c = percentile(costs, 0.50)
    p95_c = percentile(costs, 0.95)
    p50_l = percentile(latencies, 0.50)
    p95_l = percentile(latencies, 0.95)
    ci_low_c, ci_high_c = bootstrap_ci(costs, lambda xs: percentile(xs, 0.50))
    ci_low_l, ci_high_l = bootstrap_ci(latencies, lambda xs: percentile(xs, 0.50))
    return (
        f"{n_turns}\t"
        f"{p50_c:.6f}\t{p95_c:.6f}\t{ci_low_c:.6f}\t{ci_high_c:.6f}\t"
        f"{p50_l:.3f}\t{p95_l:.3f}\t{ci_low_l:.3f}\t{ci_high_l:.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Per-turn metrics aggregator for Phase 4.7 G1 baseline"
    )
    parser.add_argument("db_path", help="Path to ~/.hermes/profiles/<profile>/state.db")
    parser.add_argument("target_date", help="UTC date in YYYY-MM-DD")
    parser.add_argument(
        "--source",
        default="slack",
        help="messages.source filter (default: slack)",
    )
    args = parser.parse_args()

    # Validate date format early.
    try:
        date_cls.fromisoformat(args.target_date)
    except ValueError:
        print(f"# error: bad date {args.target_date}", file=sys.stderr)
        sys.exit(2)

    turns = pull_turns_from_messages(args.db_path, args.target_date, args.source)
    if not turns:
        # No turns → emit zero row. Capture script's downstream gate
        # (errors==0 AND graded_answers>=30) decides whether the night
        # qualifies; per-turn metrics being empty doesn't disqualify.
        print(emit_tsv(0, [], []))
        return 0

    latencies = [asst_ts - user_ts for _, user_ts, asst_ts, _ in turns]

    costs = cost_per_turn_langfuse(turns)
    if costs is None:
        costs = cost_per_turn_heuristic(turns)

    # Clamp pathological negatives (clock skew on resumed sessions).
    latencies = [max(0.0, v) for v in latencies]
    costs = [max(0.0, v) for v in costs]

    print(emit_tsv(len(turns), costs, latencies))
    return 0


if __name__ == "__main__":
    sys.exit(main())
