#!/usr/bin/python3
"""Unit coverage for scout-eval-summary.py — focused on the infra/billing
exclusion that keeps a credit outage from depressing the gate.

Run:  python3 scripts/test_scout_eval_summary.py
"""
import importlib.util
import json
import os
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "scout_eval_summary", os.path.join(_HERE, "scout-eval-summary.py")
)
ses = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ses)

BILLING = (
    "API call error: Your credit balance is too low to access the Anthropic "
    "API. Please go to Plans & Billing to upgrade or purchase credits."
)


def _row(provider="sonnet", success=True, output="digest body",
         error="", resp_error="", gr_reason="All assertions passed",
         comp_reasons=("ok",), fixture="active-week"):
    """Build a promptfoo result row matching the real --output JSON shape."""
    return {
        "provider": {"label": provider},
        "success": success,
        "error": error,
        "response": {"output": output, "error": resp_error},
        "testCase": {"description": fixture},
        "gradingResult": {
            "pass": success,
            "reason": gr_reason,
            "componentResults": [
                {"pass": success, "reason": r} for r in comp_reasons
            ],
        },
    }


def _write_run(rows):
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"results": {"results": rows}}, fh)
    return path


class InfraErrorMatcher(unittest.TestCase):
    def test_grader_credit_exhaustion_is_infra(self):
        # Grader call ran out of credits: model output fine, billing string in
        # row.error + gradingResult.reason, failureReason=1.
        row = _row(success=False, error=BILLING, gr_reason=BILLING,
                   comp_reasons=(BILLING,))
        self.assertIsNotNone(ses.infra_error(row))

    def test_provider_credit_exhaustion_empty_output_is_infra(self):
        # Model-under-test call errored: empty output, billing string in
        # response.error, blank grading reason, failureReason=2.
        row = _row(success=False, output="", error=BILLING, resp_error=BILLING,
                   gr_reason="", comp_reasons=())
        self.assertIsNotNone(ses.infra_error(row))

    def test_empty_output_blank_reason_no_signature_is_infra(self):
        # No recognizable billing string, but the row produced no gradable
        # signal at all (empty output + blank grader reason + failed) — that is
        # an infra/grading breakdown, not a content judgement.
        row = _row(success=False, output="", error="", resp_error="",
                   gr_reason="", comp_reasons=())
        self.assertIsNotNone(ses.infra_error(row))

    def test_real_content_failure_is_not_infra(self):
        # Real output, grader gives a genuine content critique — must NOT be
        # swept into the infra bucket.
        row = _row(success=False,
                   gr_reason="Finding F1 cites no source.",
                   comp_reasons=("Finding F1 cites no source.",))
        self.assertIsNone(ses.infra_error(row))

    def test_empty_output_with_real_grader_reason_is_not_infra(self):
        # Empty output but the grader explained why it failed — a real failure.
        row = _row(success=False, output="",
                   gr_reason="Output is empty; no findings reported.",
                   comp_reasons=("Output is empty; no findings reported.",))
        self.assertIsNone(ses.infra_error(row))

    def test_passing_row_is_not_infra(self):
        self.assertIsNone(ses.infra_error(_row(success=True)))


class GateBehaviour(unittest.TestCase):
    def test_billing_rows_drop_out_of_denominator(self):
        # 3 real passing rows + 5 billing errors per funded provider. The true
        # rate is 3/3=100%, not 3/8 — and the gate must PASS, not FAIL.
        rows = []
        for prov in ("sonnet", "haiku"):
            rows += [_row(prov, success=True) for _ in range(3)]
            rows += [_row(prov, success=False, output="", error=BILLING,
                          resp_error=BILLING, gr_reason="", comp_reasons=())
                     for _ in range(5)]
        s = ses.summarize(_write_run(rows))
        self.assertEqual(s["providers"]["sonnet"]["total"], 3)
        self.assertEqual(s["providers"]["sonnet"]["passed"], 3)
        self.assertEqual(s["providers"]["sonnet"]["errors"], 5)
        self.assertEqual(s["providers"]["sonnet"]["rate"], 1.0)
        self.assertEqual(s["gate"], "PASS")
        self.assertEqual(len(s["infra_errors"]), 10)

    def test_all_billing_rows_report_no_fundable_rows(self):
        # Every funded row is a credit-exhaustion error → there is no evidence
        # to judge. Must report "NO FUNDABLE ROWS", never a false FAIL with a
        # bogus low rate.
        rows = []
        for prov in ("sonnet", "haiku"):
            rows += [_row(prov, success=False, error=BILLING, gr_reason=BILLING,
                          comp_reasons=(BILLING,)) for _ in range(20)]
        s = ses.summarize(_write_run(rows))
        self.assertEqual(s["gate"], "NO FUNDABLE ROWS")
        self.assertEqual(s["providers"]["sonnet"]["total"], 0)
        self.assertEqual(len(s["infra_errors"]), 40)

    def test_real_failures_still_fail_the_gate(self):
        # No billing noise — genuine content failures below threshold must
        # still FAIL. The fix must not neuter the gate.
        rows = []
        for prov in ("sonnet", "haiku"):
            rows += [_row(prov, success=True) for _ in range(2)]
            rows += [_row(prov, success=False,
                          gr_reason="No verdict on finding.",
                          comp_reasons=("No verdict on finding.",))
                     for _ in range(8)]
        s = ses.summarize(_write_run(rows))
        self.assertEqual(s["providers"]["sonnet"]["total"], 10)
        self.assertEqual(s["gate"], "FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
