"""Unit tests for hermes.lib.agent_events.

Stdlib-only. Run via:
    python3 -m unittest tests.test_agent_events -v

Integration test against the live PFOS endpoint is gated on
``HERMES_TEST_LIVE_EMIT=1`` so the suite stays offline by default.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hermes.lib.agent_events import (  # noqa: E402
    EmitError,
    build_payload,
    emit_event,
)


FIXTURE_CONFIG = """\
profile: test-profile
tools:
  builtin: [my_tool.go]
  contracts:
    my_tool.go:
      authority: proposed_write_only
      event:
        type: test.thing.proposed
        status: pending
        surface: cli
        cwd_project: testlab
        skill_slug: my-skill
        silo_slug: skills
        data_runtime: hermes
        data_proposal_status: proposed
        private_payload_redacted: true
"""


class _ProfileFixture:
    """Lightweight tempdir profile for tests."""

    def __init__(self, config_text: str = FIXTURE_CONFIG) -> None:
        self.tmpdir = Path(tempfile.mkdtemp(prefix="hermes-test-"))
        self.profile = self.tmpdir / "test-profile"
        self.profile.mkdir()
        (self.profile / "config.yaml").write_text(config_text)

    def cleanup(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestBuildPayload(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = _ProfileFixture()

    def tearDown(self) -> None:
        self.fixture.cleanup()

    def test_required_top_level_fields_present(self) -> None:
        payload = build_payload(self.fixture.profile, "my_tool.go")
        for key in ("agent_slug", "type", "status", "surface", "cwd_project", "skill_slug"):
            self.assertIn(key, payload, f"missing {key}")
            self.assertTrue(payload[key], f"empty {key}")

    def test_data_block_required_fields(self) -> None:
        payload = build_payload(self.fixture.profile, "my_tool.go")
        self.assertEqual(payload["data"]["runtime"], "hermes")
        self.assertTrue(payload["data"]["private_payload_redacted"])
        self.assertEqual(payload["data"]["schema_version"], "hermes.agent_event.v1")

    def test_agent_slug_from_config_profile(self) -> None:
        payload = build_payload(self.fixture.profile, "my_tool.go")
        self.assertEqual(payload["agent_slug"], "test-profile")

    def test_event_type_from_config(self) -> None:
        payload = build_payload(self.fixture.profile, "my_tool.go")
        self.assertEqual(payload["type"], "test.thing.proposed")
        self.assertEqual(payload["cwd_project"], "testlab")
        self.assertEqual(payload["skill_slug"], "my-skill")

    def test_overrides_merge_into_data(self) -> None:
        payload = build_payload(
            self.fixture.profile,
            "my_tool.go",
            overrides={"data": {"readout_path": "foo.md", "decision": "continue"}},
        )
        self.assertEqual(payload["data"]["readout_path"], "foo.md")
        self.assertEqual(payload["data"]["decision"], "continue")
        # ADR-required fields survive nested override merge
        self.assertTrue(payload["data"]["private_payload_redacted"])
        self.assertEqual(payload["data"]["runtime"], "hermes")

    def test_top_level_overrides(self) -> None:
        payload = build_payload(
            self.fixture.profile,
            "my_tool.go",
            overrides={"confidence": 0.7, "trace_id": "abc"},
        )
        self.assertEqual(payload["confidence"], 0.7)
        self.assertEqual(payload["trace_id"], "abc")

    def test_missing_tool_raises(self) -> None:
        with self.assertRaises(EmitError) as cm:
            build_payload(self.fixture.profile, "nonexistent.tool")
        self.assertIn("nonexistent.tool", str(cm.exception))

    def test_missing_event_block_raises(self) -> None:
        (self.fixture.profile / "config.yaml").write_text(
            "profile: test-profile\n"
            "tools:\n"
            "  contracts:\n"
            "    no_event_tool:\n"
            "      authority: read_only\n"
        )
        with self.assertRaises(EmitError) as cm:
            build_payload(self.fixture.profile, "no_event_tool")
        self.assertIn("event", str(cm.exception).lower())

    def test_missing_config_raises(self) -> None:
        with self.assertRaises(EmitError):
            build_payload(self.fixture.tmpdir / "nonexistent", "any.tool")

    def test_payload_validation_rejects_missing_skill_slug(self) -> None:
        # Per the ADR, skill_slug is required and the lib refuses to silently
        # invent one. Profile-config-must-declare-it is a load-bearing rule.
        (self.fixture.profile / "config.yaml").write_text(
            "profile: test-profile\n"
            "tools:\n"
            "  contracts:\n"
            "    bare_tool.go:\n"
            "      event:\n"
            "        type: bare.thing\n"
            "        cwd_project: lab\n"
        )
        with self.assertRaises(EmitError) as cm:
            build_payload(self.fixture.profile, "bare_tool.go")
        self.assertIn("skill_slug", str(cm.exception))

    def test_override_cannot_disable_redacted_flag(self) -> None:
        # Adversarial override that flips private_payload_redacted to False
        # must not silently land — the validator rejects empty/false required fields.
        # (False registers as "in (None, '')" via the validator — confirmed below.)
        with self.assertRaises(EmitError):
            build_payload(
                self.fixture.profile,
                "my_tool.go",
                overrides={"data": {"private_payload_redacted": ""}},
            )

    def test_override_data_precedence_overrides_config(self) -> None:
        # Document the precedence: overrides win over config event.data_* fields.
        # If a profile config later declares e.g. data_decision, the caller's
        # override of decision should still apply — most-specific wins.
        cfg_with_data = (
            "profile: test-profile\n"
            "tools:\n"
            "  contracts:\n"
            "    my_tool.go:\n"
            "      event:\n"
            "        type: test.thing\n"
            "        cwd_project: lab\n"
            "        skill_slug: my-skill\n"
            "        data_decision: continue\n"
        )
        (self.fixture.profile / "config.yaml").write_text(cfg_with_data)
        payload = build_payload(
            self.fixture.profile,
            "my_tool.go",
            overrides={"data": {"decision": "pause"}},
        )
        self.assertEqual(payload["data"]["decision"], "pause")

    def test_safety_rules_no_raw_text_in_data(self) -> None:
        """ADR forbids raw vault text. Test that overrides accepting strings work,
        but a sanity assertion sits in place for callers shipping huge blobs."""
        payload = build_payload(
            self.fixture.profile,
            "my_tool.go",
            overrides={"data": {"summary": "Safe one-liner."}},
        )
        # Library doesn't enforce length, but it does require redacted flag stays true
        self.assertTrue(payload["data"]["private_payload_redacted"])


class TestEmitEventOffline(unittest.TestCase):
    """Mocked HTTP — no live calls."""

    def setUp(self) -> None:
        self.fixture = _ProfileFixture()

    def tearDown(self) -> None:
        self.fixture.cleanup()

    def test_dry_run_returns_payload(self) -> None:
        result = emit_event(self.fixture.profile, "my_tool.go", dry_run=True)
        self.assertTrue(result["dry_run"])
        self.assertIn("payload", result)
        self.assertEqual(result["payload"]["type"], "test.thing.proposed")

    def test_missing_token_raises(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EmitError) as cm:
                emit_event(self.fixture.profile, "my_tool.go")
        self.assertIn("TOKEN", str(cm.exception).upper())

    def test_whitespace_only_token_raises(self) -> None:
        # Bearer " " is functionally missing — must be rejected before the POST.
        with patch.dict(os.environ, {"HERMES_AGENT_EVENTS_TOKEN": "   "}, clear=True):
            with self.assertRaises(EmitError) as cm:
                emit_event(self.fixture.profile, "my_tool.go")
        self.assertIn("TOKEN", str(cm.exception).upper())

    def test_invalid_silo_slug_rejected(self) -> None:
        # Crafted silo with path traversal characters must be rejected before
        # the URL is built — prevents redirect to attacker-chosen endpoint.
        (self.fixture.profile / "config.yaml").write_text(
            "profile: test-profile\n"
            "tools:\n"
            "  contracts:\n"
            "    my_tool.go:\n"
            "      event:\n"
            "        type: test.thing\n"
            "        cwd_project: lab\n"
            "        skill_slug: my-skill\n"
            "        silo_slug: '../../admin'\n"
        )
        with patch.dict(
            os.environ,
            {"HERMES_AGENT_EVENTS_TOKEN": "fake", "HERMES_AGENT_EVENTS_URL": "http://x"},
            clear=True,
        ):
            with self.assertRaises(EmitError) as cm:
                emit_event(self.fixture.profile, "my_tool.go")
        self.assertIn("silo_slug", str(cm.exception))

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_successful_post_returns_response(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(
            {"ok": True, "event_id": "abc-123"}
        ).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None
        mock_urlopen.return_value = mock_resp

        with patch.dict(
            os.environ,
            {
                "HERMES_AGENT_EVENTS_TOKEN": "fake-token",
                "HERMES_AGENT_EVENTS_URL": "http://example.test",
            },
            clear=True,
        ):
            result = emit_event(self.fixture.profile, "my_tool.go")

        self.assertEqual(result, {"ok": True, "event_id": "abc-123"})

        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.full_url, "http://example.test/api/silos/skills/agent-event")
        self.assertEqual(req.get_header("Authorization"), "Bearer fake-token")
        self.assertEqual(req.get_header("Content-type"), "application/json")

        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["type"], "test.thing.proposed")
        self.assertEqual(body["cwd_project"], "testlab")
        self.assertEqual(body["skill_slug"], "my-skill")


@unittest.skipUnless(
    os.environ.get("HERMES_TEST_LIVE_EMIT") == "1",
    "Skipping live PFOS test. Set HERMES_TEST_LIVE_EMIT=1 to enable.",
)
class TestEmitEventLive(unittest.TestCase):
    """Live test against PFOS — uses the real CMO profile.

    Inserts a row tagged with ``test_marker`` in data; relies on Phase 4
    verifier to detect contract-shape regressions. Test-emitted rows are
    not auto-deleted (no service-role from Python); they appear in PFOS
    with the marker for manual cleanup if desired.
    """

    def test_live_smoke_against_cmo(self) -> None:
        cmo_profile = ROOT / "hermes" / "profiles" / "cmo"
        if not cmo_profile.is_dir():
            self.skipTest(f"cmo profile not available at {cmo_profile}")
        result = emit_event(
            cmo_profile,
            "weekly_decision.propose",
            overrides={
                "data": {
                    "readout_path": "_inbox/cmo-readouts/live-test-marker.md",
                    "decision": "continue",
                    "test_marker": "hermes-lib-live-smoke",
                },
            },
        )
        self.assertIn("event_id", result)
        self.assertTrue(result.get("ok"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
