#!/usr/bin/python3
"""
scout-eval-summary.py — score a scout-eval promptfoo run.

Reads the JSON promptfoo writes (`promptfoo eval --output <file>.json`) and
reports, per under-test provider: overall pass-rate + Wilson lower-CI (95%) +
a per-fixture breakdown, then the GATE verdict.

Gate (per feedback_audit_quality_eval_gated_skill_shipping): ≥80% pass on BOTH
the real synthesis model (sonnet) AND the robustness model (haiku). The free
nemotron smoke model is marked synthetic and excluded from the gate — mirrors
vanclief-eval-summary.py's is_synthetic exclusion. Wilson lower-CI mirrors
scripts/lib/wilson.sh.

Usage:
  python3 scripts/scout-eval-summary.py <run.json>          # human-readable
  python3 scripts/scout-eval-summary.py <run.json> --json   # machine-readable
"""
import argparse
import json
import math
import sys
from collections import defaultdict

GATE_PASS_RATE = 0.80
# Providers whose label/id matches these are smoke-only — excluded from the gate.
SMOKE_MARKERS = ("nemotron", "smoke")
# Substrings that mark a row as an infra/billing error (not a content failure).
# Such rows are excluded from the pass/total denominator — a 402 or a network
# blip must not depress the gate. Mirrors promptfoo's error-vs-failure split.
INFRA_ERROR_MARKERS = (
    "api error", "payment required", "insufficient credits", "402",
    "429", "rate limit", "timeout", "timed out", "econnreset",
    "fetch failed", "socket hang up", "500 ", "502", "503", "529",
    "service unavailable", "overloaded",
)


def wilson_lower(k: int, n: int) -> float:
    """Wilson 95% lower confidence bound — mirrors scripts/lib/wilson.sh."""
    if n == 0:
        return 0.0
    z = 1.96
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = (z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n)) / denom
    return max(0.0, centre - margin)


def is_smoke(label: str) -> bool:
    lab = (label or "").lower()
    return any(m in lab for m in SMOKE_MARKERS)


def load_rows(path):
    data = json.load(open(path, encoding="utf-8"))
    return data.get("results", {}).get("results", []) or []


def provider_label(row):
    prov = row.get("provider", {}) or {}
    return prov.get("label") or prov.get("id") or "unknown"


def test_label(row):
    tc = row.get("testCase", {}) or {}
    desc = tc.get("description")
    if desc:
        return desc
    fx = (tc.get("vars", {}) or row.get("vars", {}) or {}).get("fixture", "")
    return str(fx)


def infra_error(row):
    """Return the infra/billing error string if this row failed for a non-content
    reason (API 402, rate limit, network), else None."""
    err = (row.get("error") or "")
    resp = row.get("response", {}) or {}
    blob = " ".join([str(err), str(resp.get("error") or "")]).lower()
    if any(m in blob for m in INFRA_ERROR_MARKERS):
        return (err or resp.get("error") or "infra error").strip().replace("\n", " ")[:160]
    return None


def failure_reason(row):
    """Pull the first failing grader reason from a result row."""
    gr = row.get("gradingResult", {}) or {}
    comps = gr.get("componentResults") or [gr]
    for c in comps:
        if not c.get("pass", True):
            return (c.get("reason") or "").strip().replace("\n", " ")
    return (gr.get("reason") or "").strip().replace("\n", " ")


def output_excerpt(row, n=400):
    out = (row.get("response", {}) or {}).get("output") or ""
    return out[:n].replace("\n", " ")


def summarize(path):
    rows = load_rows(path)
    # provider -> {"k":passed, "n":scored_total, "errs":infra_errors, "byfix": {fixture: [k,n]}}
    prov = defaultdict(lambda: {"k": 0, "n": 0, "errs": 0, "byfix": defaultdict(lambda: [0, 0])})
    failures = []
    infra_errors = []
    for r in rows:
        pl = provider_label(r)
        tl = test_label(r)
        ierr = infra_error(r)
        if ierr:
            # Infra/billing error — excluded from the scored denominator.
            prov[pl]["errs"] += 1
            if not is_smoke(pl):
                infra_errors.append({
                    "provider": pl,
                    "fixture": tl.replace("file://fixtures/", "").replace(".md", ""),
                    "error": ierr,
                })
            continue
        ok = 1 if r.get("success") else 0
        prov[pl]["k"] += ok
        prov[pl]["n"] += 1
        prov[pl]["byfix"][tl][0] += ok
        prov[pl]["byfix"][tl][1] += 1
        if not ok and not is_smoke(pl):
            failures.append({
                "provider": pl,
                "fixture": tl.replace("file://fixtures/", "").replace(".md", ""),
                "reason": failure_reason(r)[:300],
                "output_excerpt": output_excerpt(r),
            })

    providers = {}
    gate_inputs = []
    for pl, d in sorted(prov.items()):
        k, n = d["k"], d["n"]
        rate = round(k / n, 4) if n else None
        lci = round(wilson_lower(k, n), 4)
        smoke = is_smoke(pl)
        providers[pl] = {
            "passed": k, "total": n, "errors": d["errs"],
            "rate": rate, "wilson_lower_ci": lci, "smoke": smoke,
            "by_fixture": {fx: {"passed": kk, "total": nn,
                                "rate": round(kk / nn, 4) if nn else None}
                           for fx, (kk, nn) in sorted(d["byfix"].items())},
        }
        if not smoke:
            # n==0 → every row errored; rate is unreadable, treat as a gate miss.
            gate_inputs.append((pl, rate if (rate is not None and n > 0) else -1.0))

    # Gate: every funded (non-smoke) provider must clear the pass-rate bar on a
    # readable (n>0) sample, and there must be at least one funded provider.
    gate = "PASS" if gate_inputs and all(r >= GATE_PASS_RATE for _, r in gate_inputs) else "FAIL"
    return {
        "run": path,
        "gate": gate,
        "gate_threshold": GATE_PASS_RATE,
        "gate_providers": [pl for pl, _ in gate_inputs],
        "providers": providers,
        "failures": failures,
        "infra_errors": infra_errors,
    }


def print_human(s):
    print(f"scout-eval summary — {s['run']}")
    print("=" * 64)
    print(f"GATE (≥{int(s['gate_threshold']*100)}% on {', '.join(s['gate_providers']) or '—'}, smoke excluded): {s['gate']}")
    for pl, p in s["providers"].items():
        tag = " (smoke · excluded)" if p["smoke"] else ""
        mark = "✓" if (not p["smoke"] and p["total"] and (p["rate"] or 0) >= s["gate_threshold"]) else (" " if p["smoke"] else "✗")
        errnote = f"  [{p['errors']} infra-error rows excluded]" if p.get("errors") else ""
        print(f"\n  {mark} {pl}{tag}: {p['passed']}/{p['total']} = {p['rate']}  (Wilson lower-CI {p['wilson_lower_ci']}){errnote}")
        for fx, f in p["by_fixture"].items():
            short = fx.replace("file://fixtures/", "").replace(".md", "")
            print(f"        {f['passed']}/{f['total']}  {short}")
    if s.get("infra_errors"):
        print(f"\n  ⚠ {len(s['infra_errors'])} infra/billing error rows excluded from the gate "
              f"(e.g. {s['infra_errors'][0]['error'][:60]})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="path to promptfoo --output JSON")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    s = summarize(args.run)
    if args.json:
        print(json.dumps(s, indent=2))
    else:
        print_human(s)
    # Exit non-zero when the gate fails — lets callers/CI branch on it.
    return 0 if s["gate"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
