"""Tests for scripts/verify-event-contract.

The verifier compares recent ``agent_events`` rows against each profile's
declared ``event:`` block in ``config.yaml`` and reports violations.

Run via:
    python3 -m unittest tests.test_verify_event_contract -v
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFIER_PATH = ROOT / "scripts" / "verify-event-contract.py"

# Import the script as a module (file has a dash in its name)
_spec = importlib.util.spec_from_file_location("verify_event_contract", VERIFIER_PATH)
verify_event_contract = importlib.util.module_from_spec(_spec)
sys.modules["verify_event_contract"] = verify_event_contract
_spec.loader.exec_module(verify_event_contract)


PROFILE_CONFIG = """\
profile: test-profile
tools:
  contracts:
    weekly_decision.propose:
      authority: proposed_write_only
      event:
        type: test-profile.weekly_decision.proposed
        status: pending
        surface: cli
        cwd_project: testlab
        skill_slug: weekly-review
        silo_slug: skills
        data_runtime: hermes
        private_payload_redacted: true
"""

# Reference event rows — these match the contract above
COMPLIANT_ROW = {
    "id": "00000000-0000-0000-0000-000000000001",
    "type": "test-profile.weekly_decision.proposed",
    "status": "pending",
    "surface": "cli",
    "cwd_project": "testlab",
    "skill_slug": "weekly-review",
    "data": {"runtime": "hermes", "private_payload_redacted": True},
    "created_at": "2026-05-19T10:00:00+00:00",
}


def _row(**overrides) -> dict:
    row = json.loads(json.dumps(COMPLIANT_ROW))
    for key, value in overrides.items():
        if "." in key:
            head, tail = key.split(".", 1)
            row.setdefault(head, {})[tail] = value
        else:
            row[key] = value
    return row


class TestVerifyEventContract(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="hermes-verify-"))
        self.profile = self.tmpdir / "test-profile"
        self.profile.mkdir()
        (self.profile / "config.yaml").write_text(PROFILE_CONFIG)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_compliant_row_passes(self) -> None:
        violations = verify_event_contract.verify_rows([_row()], [self.profile])
        self.assertEqual(violations, [])

    def test_null_cwd_project_fails(self) -> None:
        violations = verify_event_contract.verify_rows(
            [_row(cwd_project=None)],
            [self.profile],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("cwd_project", violations[0]["field"])

    def test_null_skill_slug_fails(self) -> None:
        violations = verify_event_contract.verify_rows(
            [_row(skill_slug=None)],
            [self.profile],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("skill_slug", violations[0]["field"])

    def test_wrong_cwd_project_value_fails(self) -> None:
        violations = verify_event_contract.verify_rows(
            [_row(cwd_project="WRONG")],
            [self.profile],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("cwd_project", violations[0]["field"])
        self.assertIn("WRONG", violations[0]["actual"])
        self.assertIn("testlab", violations[0]["expected"])

    def test_missing_data_runtime_fails(self) -> None:
        row = _row()
        row["data"] = {"private_payload_redacted": True}  # no runtime
        violations = verify_event_contract.verify_rows([row], [self.profile])
        self.assertEqual(len(violations), 1)
        self.assertIn("data.runtime", violations[0]["field"])

    def test_redacted_false_fails(self) -> None:
        violations = verify_event_contract.verify_rows(
            [_row(**{"data.private_payload_redacted": False})],
            [self.profile],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("private_payload_redacted", violations[0]["field"])

    def test_row_with_unknown_type_is_skipped(self) -> None:
        # Rows whose type doesn't match any declared event in our profiles
        # are skipped (not our contract to enforce).
        violations = verify_event_contract.verify_rows(
            [_row(type="unrelated.thing")],
            [self.profile],
        )
        self.assertEqual(violations, [])

    def test_multiple_rows_aggregated(self) -> None:
        violations = verify_event_contract.verify_rows(
            [
                _row(),
                _row(cwd_project=None, id="00000000-0000-0000-0000-000000000002"),
                _row(skill_slug=None, id="00000000-0000-0000-0000-000000000003"),
            ],
            [self.profile],
        )
        # 2 violations, both from rows 2 and 3
        self.assertEqual(len(violations), 2)
        bad_ids = {v["row_id"] for v in violations}
        self.assertEqual(
            bad_ids,
            {"00000000-0000-0000-0000-000000000002", "00000000-0000-0000-0000-000000000003"},
        )


class TestLoadEventDeclarations(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="hermes-verify-"))
        self.profile = self.tmpdir / "test-profile"
        self.profile.mkdir()
        (self.profile / "config.yaml").write_text(PROFILE_CONFIG)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_extracts_event_blocks_keyed_by_type(self) -> None:
        decls = verify_event_contract.load_event_declarations([self.profile])
        self.assertIn("test-profile.weekly_decision.proposed", decls)
        decl = decls["test-profile.weekly_decision.proposed"]
        self.assertEqual(decl["cwd_project"], "testlab")
        self.assertEqual(decl["skill_slug"], "weekly-review")


if __name__ == "__main__":
    unittest.main(verbosity=2)
