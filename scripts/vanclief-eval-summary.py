#!/usr/bin/python3
"""
vanclief-eval-summary.py — consumer side of the eval_trace bus.

Reads eval_trace messages from `prettyfly-os/eval-traces-{YYYY-MM}` and
produces a per-SKU rollup: trial count, latest Wilson lower-CI, gate
status, providers represented. This is the basis of VanClief's Sunday
Brief eval section.

Phase 1 substrate-as-bus claim, completed:
  Producer: scripts/email-triage-eval-nightly.sh (publishes per-provider trace)
  Bus:      Honcho session `eval-traces-{YYYY-MM}`
  Consumer: this script (reads + summarizes)

Gate (per architecture decision #5):
  Wilson lower-CI ≥ 0.80 AND median rate ≥ 0.85 across ≥ 2 funded providers.

Usage:
  python3 scripts/vanclief-eval-summary.py                # current month
  python3 scripts/vanclief-eval-summary.py --month 2026-05
  python3 scripts/vanclief-eval-summary.py --json         # machine-readable
"""
import argparse
import json
import os
import sys
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest

import jwt as pyjwt

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "honcho" / ".env"
HONCHO_URL = os.environ.get("HONCHO_URL", "http://localhost:8765")
WORKSPACE_ID = os.environ.get("HONCHO_WORKSPACE", "prettyfly-os")


def read_jwt_secret():
    if not ENV_FILE.is_file():
        raise SystemExit(f"FATAL: {ENV_FILE} missing")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("HONCHO_JWT_SECRET="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("FATAL: HONCHO_JWT_SECRET not set")


def fetch_traces(session_id: str):
    secret = read_jwt_secret()
    token = pyjwt.encode({"ad": True}, secret, algorithm="HS256")
    url = f"{HONCHO_URL}/v3/workspaces/{WORKSPACE_ID}/sessions/{session_id}/messages/list"
    req = urlrequest.Request(url, data=b"{}", method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with urlrequest.urlopen(req, timeout=10) as r:
        body = json.loads(r.read())
    items = body.get("items", body if isinstance(body, list) else [])
    traces = []
    for m in items:
        try:
            payload = json.loads(m.get("content", ""))
        except Exception:
            continue
        if payload.get("event_type") != "eval_trace":
            continue
        traces.append(payload)
    return traces


SYNTHETIC_PROVIDER_PREFIXES = ("smoke-test", "smoke:", "debug:", "test:", "synthetic:")


def is_synthetic(provider: str) -> bool:
    p = (provider or "").lower()
    return any(p.startswith(pref) for pref in SYNTHETIC_PROVIDER_PREFIXES)


def gate_status(rates, lower_cis, threshold_lower=0.80, threshold_median=0.85):
    """Per decision #5: Wilson lower-CI ≥ 0.80 AND median rate ≥ 0.85 across ≥ 2 providers.
    Caller is responsible for filtering synthetic providers before calling."""
    funded = [(r, lc) for r, lc in zip(rates, lower_cis) if lc >= threshold_lower and r >= threshold_median]
    if len(funded) >= 2:
        return "PASS"
    return "FAIL"


def summarize(traces, as_json=False):
    by_sku = defaultdict(list)
    for t in traces:
        by_sku[t.get("sku", "unknown")].append(t)

    summary = {
        "total_traces": len(traces),
        "skus": {},
    }

    for sku, items in sorted(by_sku.items()):
        # Group by provider, take the latest trace per (sku, provider, date)
        by_provider = defaultdict(list)
        for t in items:
            by_provider[t.get("provider", "unknown")].append(t)

        providers = []
        rates_for_gate = []
        lower_cis_for_gate = []
        for provider, traces_list in by_provider.items():
            latest = max(traces_list, key=lambda x: (x.get("date", ""), x.get("manifest_hash", "")))
            synthetic = is_synthetic(provider)
            providers.append({
                "provider": provider,
                "latest_date": latest.get("date"),
                "passed": latest.get("passed"),
                "total": latest.get("total"),
                "rate": latest.get("rate"),
                "wilson_lower_ci": latest.get("wilson_lower_ci"),
                "trace_count": len(traces_list),
                "synthetic": synthetic,
            })
            # Synthetic providers are excluded from gate computation.
            if not synthetic:
                rates_for_gate.append(latest.get("rate", 0.0))
                lower_cis_for_gate.append(latest.get("wilson_lower_ci", 0.0))

        gate = gate_status(rates_for_gate, lower_cis_for_gate)
        summary["skus"][sku] = {
            "trace_count": len(items),
            "provider_count": len(providers),
            "median_rate": round(statistics.median(rates_for_gate), 4) if rates_for_gate else None,
            "median_lower_ci": round(statistics.median(lower_cis_for_gate), 4) if lower_cis_for_gate else None,
            "gate": gate,
            "providers": providers,
        }

    if as_json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"VanClief eval rollup — {summary['total_traces']} trace(s) total")
        print("=" * 60)
        for sku, s in summary["skus"].items():
            print(f"\nSKU: {sku}")
            print(f"  Gate (≥2 providers @ rate≥0.85, lower-CI≥0.80): {s['gate']}")
            print(f"  Median rate: {s['median_rate']}  median lower-CI: {s['median_lower_ci']}")
            print(f"  Providers ({s['provider_count']}):")
            for p in sorted(s["providers"], key=lambda x: x["wilson_lower_ci"] or 0, reverse=True):
                rate = p["rate"]
                lci = p["wilson_lower_ci"]
                tag = " (synthetic)" if p.get("synthetic") else ""
                if p.get("synthetic"):
                    marker = "·"
                elif (rate or 0) >= 0.85 and (lci or 0) >= 0.80:
                    marker = "✓"
                else:
                    marker = " "
                print(f"    {marker} {p['provider']}{tag}: {p['passed']}/{p['total']} = {rate} (lower-CI {lci}) [{p['trace_count']} trace(s)]")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=datetime.now(timezone.utc).strftime("%Y-%m"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    session_id = f"eval-traces-{args.month}"
    traces = fetch_traces(session_id)
    summarize(traces, as_json=args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
