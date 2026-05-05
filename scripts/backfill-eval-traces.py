#!/usr/bin/python3
"""
backfill-eval-traces.py — replay rows from _nightly-history.tsv into the agora.

The eval_trace publish wiring landed mid-day 2026-05-05; runs from earlier
that day and from 2026-05-04 are in the TSV but never made it to Honcho.
This script publishes them retroactively so vanclief's rollup has full
history.

Marks each backfilled trace with `"backfilled": True` and a synthetic
manifest_hash prefixed `backfill-` so consumers can tell them apart from
forward-flowing traces.

Idempotent re-runs add duplicate messages — the agora will accept them.
Only run this once per fresh history; for safety, the script refuses to
publish more than 50 rows in a single invocation.

Usage:
  python3 scripts/backfill-eval-traces.py
  python3 scripts/backfill-eval-traces.py --dry-run
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TSV = ROOT / "marketplace/manifests/email-triage/eval-suite/runs/_nightly-history.tsv"
PUBLISH = ROOT / "scripts/honcho-publish-eval-trace.py"
MAX_ROWS = 50


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not TSV.is_file():
        print(f"FATAL: {TSV} missing", file=sys.stderr)
        return 1
    if not PUBLISH.is_file():
        print(f"FATAL: {PUBLISH} missing", file=sys.stderr)
        return 1

    rows = []
    for raw in TSV.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("date\t"):
            continue
        parts = raw.split("\t")
        if len(parts) < 6:
            continue
        date, provider, rate, passed, total, lower = parts[:6]
        try:
            payload = {
                "event_type": "eval_trace",
                "sku": "email-triage",
                "provider": provider,
                "date": date,
                "passed": int(passed),
                "total": int(total),
                "rate": float(rate),
                "wilson_lower_ci": float(lower),
                "manifest_hash": f"backfill-{date}-{provider}",
                "report_path": f"runs/{date}-{provider.replace(':','_').replace('/','_')}.json",
                "backfilled": True,
            }
        except (ValueError, IndexError) as e:
            print(f"SKIP: malformed row: {raw[:80]} ({e})", file=sys.stderr)
            continue
        rows.append(payload)

    if len(rows) > MAX_ROWS:
        print(f"FATAL: {len(rows)} rows exceeds MAX_ROWS={MAX_ROWS} — refuse to flood agora", file=sys.stderr)
        return 1

    print(f"Backfilling {len(rows)} eval_trace row(s) {'(dry-run)' if args.dry_run else ''}")
    published = 0
    for r in rows:
        if args.dry_run:
            print(f"  [DRY] {r['date']} {r['provider']} rate={r['rate']} lower={r['wilson_lower_ci']}")
            continue
        proc = subprocess.run(
            [str(PUBLISH)], input=json.dumps(r), text=True, capture_output=True
        )
        if proc.returncode == 0:
            published += 1
            print(f"  ok  {r['date']} {r['provider']} rate={r['rate']}")
        else:
            print(f"  FAIL {r['date']} {r['provider']}: {proc.stderr.strip()}", file=sys.stderr)

    if not args.dry_run:
        print(f"Backfilled {published}/{len(rows)} traces.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
