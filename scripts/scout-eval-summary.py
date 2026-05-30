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
# Such rows are excluded from the pass/total denominator — a 402, an exhausted
# credit balance, or a network blip must not depress the gate. Mirrors
# promptfoo's error-vs-failure split.
#
# BILLING_MARKERS are high-specificity phrases safe to match anywhere, including
# the grader's natural-language reason: an llm-rubric reason never legitimately
# contains them. "api call error" is promptfoo's prefix when the grading call
# itself fails (e.g. the Anthropic-direct grader runs out of credits while the
# model-under-test responded fine); "credit balance"/"insufficient" are billing-
# exhaustion text. INFRA_ERROR_MARKERS adds lower-specificity HTTP/network codes
# that are only trusted in the provider/grader *error* fields (infra-origin),
# never in graded prose, to avoid false positives on numbers in a digest.
BILLING_MARKERS = (
    "api call error", "credit balance", "insufficient", "payment required",
    "rate limit", "too many requests", "service unavailable", "overloaded",
)
INFRA_ERROR_MARKERS = BILLING_MARKERS + (
    "api error", "402", "401", "429", "unauthorized",
    "timeout", "timed out", "econnreset", "fetch failed", "socket hang up",
    "500 ", "502", "503", "529",
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
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
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


def grading_reasons(row):
    """Every grader reason on a row (top-level + per-component), joined."""
    gr = row.get("gradingResult", {}) or {}
    parts = [gr.get("reason") or ""]
    parts += [c.get("reason") or "" for c in (gr.get("componentResults") or [])]
    return " ".join(p for p in parts if p)


def infra_error(row):
    """Return an infra/billing error string if this row failed for a non-content
    reason — an API 402/401/429, an exhausted credit balance, a network blip, or
    a grader call that itself errored — else None. Such rows are excluded from the
    pass/total denominator.

    Covers both failure surfaces seen with the Anthropic-direct provider when the
    account is out of credits: the model-under-test erroring (empty output, error
    on the response, failureReason=2) AND the llm-rubric grader erroring (the
    billing string surfaces in row.error / the grader reason while the model
    output is fine, failureReason=1)."""
    err = (row.get("error") or "")
    resp = row.get("response", {}) or {}
    resp_err = resp.get("error") or ""
    reasons = grading_reasons(row)
    err_blob = " ".join([str(err), str(resp_err)]).lower()
    # Numeric/network codes only in the infra-origin error fields; billing
    # phrases additionally in the grader's reason (where 402-style numbers could
    # be legitimate digest content, so they are kept out of the reason scan).
    if any(m in err_blob for m in INFRA_ERROR_MARKERS) or \
       any(m in reasons.lower() for m in BILLING_MARKERS):
        return (err or resp_err or reasons or "infra error").strip().replace("\n", " ")[:160]
    # No recognizable signature, but the row produced no gradable signal: the
    # provider response errored or the output is empty AND the grader returned a
    # blank reason. That is an infra/grading breakdown, not a content judgement.
    out = str(resp.get("output") or "").strip()
    if not row.get("success") and (resp_err or not out) and not reasons.strip():
        msg = (err or resp_err or "empty output / grader error").strip().replace("\n", " ")[:160]
        return msg or "empty output / grader error"
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
    funded = []      # all non-smoke providers in the suite
    scorable = []    # (provider, rate) for funded providers with ≥1 gradable row
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
            funded.append(pl)
            if n > 0:
                scorable.append((pl, rate))

    # Gate: every funded (non-smoke) provider with a gradable sample must clear
    # the pass-rate bar. A provider whose rows were ALL infra/billing errors
    # contributes no signal — it neither passes nor fails. If no funded provider
    # produced a gradable row (e.g. the whole run hit a credit outage), the gate
    # is "NO FUNDABLE ROWS": an infra problem, not a content regression — never a
    # false FAIL. A suite with no funded provider at all is a misconfiguration.
    if not funded:
        gate = "FAIL"
    elif not scorable:
        gate = "NO FUNDABLE ROWS"
    else:
        gate = "PASS" if all((r or 0) >= GATE_PASS_RATE for _, r in scorable) else "FAIL"
    return {
        "run": path,
        "gate": gate,
        "gate_threshold": GATE_PASS_RATE,
        "gate_providers": [pl for pl, _ in scorable],
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
        if p["smoke"]:
            mark = " "
        elif not p["total"]:
            mark = "∅"  # no gradable rows — infra/billing outage, not a content fail
        elif (p["rate"] or 0) >= s["gate_threshold"]:
            mark = "✓"
        else:
            mark = "✗"
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
