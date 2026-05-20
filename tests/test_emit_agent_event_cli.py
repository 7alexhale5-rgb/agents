"""Tests for scripts/emit-agent-event.py CLI surface.

Stdlib-only. Exercises argparse, profile resolution, and overrides-from-flags
construction. The actual emit call is mocked to keep tests offline.

Run via:
    python3 -m unittest tests.test_emit_agent_event_cli -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
CLI_PATH = ROOT / "scripts" / "emit-agent-event.py"

# Load the script as a module (file has a dash in its name)
_spec = importlib.util.spec_from_file_location("emit_agent_event_cli", CLI_PATH)
emit_cli = importlib.util.module_from_spec(_spec)
sys.modules["emit_agent_event_cli"] = emit_cli
_spec.loader.exec_module(emit_cli)


FIXTURE_CONFIG = """\
profile: test-cli-profile
tools:
  contracts:
    sample_tool.go:
      event:
        type: test-cli-profile.thing.proposed
        cwd_project: testlab
        skill_slug: sample-skill
        silo_slug: skills
"""


class _Fixture:
    def __init__(self) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="hermes-cli-test-"))
        self.profile = self.tmpdir / "test-cli-profile"
        self.profile.mkdir()
        (self.profile / "config.yaml").write_text(FIXTURE_CONFIG)

    def cleanup(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestParseArgs(unittest.TestCase):
    def test_required_args(self) -> None:
        args = emit_cli.parse_args(["--profile", "cmo", "--tool", "weekly_decision.propose"])
        self.assertEqual(args.profile, "cmo")
        self.assertEqual(args.tool, "weekly_decision.propose")
        self.assertIsNone(args.readout_path)
        self.assertIsNone(args.confidence)
        self.assertFalse(args.dry_run)

    def test_optional_flags(self) -> None:
        args = emit_cli.parse_args([
            "--profile", "cmo",
            "--tool", "weekly_decision.propose",
            "--readout-path", "_inbox/cmo-readouts/foo.md",
            "--decision", "continue",
            "--confidence", "0.7",
            "--trace-id", "abc-123",
            "--extra-json", '{"k":"v"}',
            "--dry-run",
        ])
        self.assertEqual(args.readout_path, "_inbox/cmo-readouts/foo.md")
        self.assertEqual(args.decision, "continue")
        self.assertEqual(args.confidence, 0.7)
        self.assertEqual(args.trace_id, "abc-123")
        self.assertEqual(args.extra_json, '{"k":"v"}')
        self.assertTrue(args.dry_run)


class TestResolveProfile(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _Fixture()

    def tearDown(self) -> None:
        self.fixture.cleanup()

    def test_resolve_by_absolute_path(self) -> None:
        resolved = emit_cli.resolve_profile(str(self.fixture.profile))
        self.assertEqual(resolved, self.fixture.profile.resolve())

    def test_resolve_by_name_under_hermes_profiles(self) -> None:
        # Only succeeds if hermes/profiles/cmo exists in the live repo
        cmo = ROOT / "hermes" / "profiles" / "cmo"
        if not cmo.is_dir():
            self.skipTest("cmo profile not available")
        resolved = emit_cli.resolve_profile("cmo")
        self.assertEqual(resolved, cmo.resolve())

    def test_resolve_unknown_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            emit_cli.resolve_profile("definitely-not-a-real-profile-xyz")


class TestBuildOverrides(unittest.TestCase):
    def _ns(self, **kwargs):
        defaults = {
            "readout_path": None,
            "decision": None,
            "confidence": None,
            "trace_id": None,
            "extra_json": None,
        }
        defaults.update(kwargs)
        return type("NS", (), defaults)()

    def test_empty_args_returns_empty(self) -> None:
        self.assertEqual(emit_cli.build_overrides(self._ns()), {})

    def test_flags_collapse_into_data(self) -> None:
        overrides = emit_cli.build_overrides(
            self._ns(readout_path="foo.md", decision="continue")
        )
        self.assertEqual(overrides["data"]["readout_path"], "foo.md")
        self.assertEqual(overrides["data"]["decision"], "continue")

    def test_extra_json_merges_into_data(self) -> None:
        overrides = emit_cli.build_overrides(
            self._ns(extra_json='{"summary":"safe","custom":1}')
        )
        self.assertEqual(overrides["data"]["summary"], "safe")
        self.assertEqual(overrides["data"]["custom"], 1)

    def test_extra_json_invalid_raises_systemexit(self) -> None:
        # Malformed JSON should be caught at argparse time, not at emit time
        with self.assertRaises(SystemExit):
            emit_cli.build_overrides(self._ns(extra_json="{not-json"))

    def test_top_level_passes_confidence_trace_id(self) -> None:
        overrides = emit_cli.build_overrides(
            self._ns(confidence=0.5, trace_id="t-1")
        )
        self.assertEqual(overrides["confidence"], 0.5)
        self.assertEqual(overrides["trace_id"], "t-1")


class TestMain(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _Fixture()

    def tearDown(self) -> None:
        self.fixture.cleanup()

    def test_dry_run_prints_payload(self) -> None:
        argv = [
            "--profile", str(self.fixture.profile),
            "--tool", "sample_tool.go",
            "--readout-path", "fake.md",
            "--decision", "pause",
            "--dry-run",
        ]
        from io import StringIO
        with patch("sys.stdout", new=StringIO()) as out:
            exit_code = emit_cli.main(argv)
        self.assertEqual(exit_code, 0)
        printed = json.loads(out.getvalue())
        self.assertEqual(printed["type"], "test-cli-profile.thing.proposed")
        self.assertEqual(printed["data"]["readout_path"], "fake.md")
        self.assertEqual(printed["data"]["decision"], "pause")

    def test_missing_profile_returns_2(self) -> None:
        argv = ["--profile", "no-such-profile-xyz", "--tool", "sample_tool.go", "--dry-run"]
        with patch("sys.stderr"):
            exit_code = emit_cli.main(argv)
        self.assertEqual(exit_code, 2)

    def test_emit_error_returns_1(self) -> None:
        # Tool exists in config but no token → EmitError → exit 1
        argv = ["--profile", str(self.fixture.profile), "--tool", "sample_tool.go"]
        with patch.dict(os.environ, {}, clear=True), patch("sys.stderr"):
            exit_code = emit_cli.main(argv)
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
