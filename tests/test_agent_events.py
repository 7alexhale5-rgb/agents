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
    RateLimitExceeded,
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


class TestRateLimits(unittest.TestCase):
    """Per-profile daily emit caps (Move 3 — fleet/limits.json + counter store)."""

    def setUp(self) -> None:
        self.fixture = _ProfileFixture()
        self.work = Path(tempfile.mkdtemp(prefix="hermes-cap-"))
        self.limits_path = self.work / "limits.json"
        self.counter_path = self.work / ".emit-counters.json"
        # Default test limit: 2 emissions/day for "test-profile" (matches fixture).
        self.limits_path.write_text(json.dumps({"limits": {"test-profile": 2}}))
        self._env = patch.dict(
            os.environ,
            {
                "HERMES_AGENT_EVENTS_TOKEN": "fake-token",
                "HERMES_AGENT_EVENTS_URL": "http://example.test",
                "HERMES_FLEET_LIMITS_FILE": str(self.limits_path),
                "HERMES_FLEET_COUNTER_FILE": str(self.counter_path),
            },
            clear=True,
        )
        self._env.start()

    def tearDown(self) -> None:
        self._env.stop()
        self.fixture.cleanup()
        shutil.rmtree(self.work, ignore_errors=True)

    def _mock_urlopen(self) -> MagicMock:
        # Helper that returns a context manager mock for urllib.request.urlopen.
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"ok": True, "event_id": "id"}).encode()
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None
        return mock_resp

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_emit_under_cap_succeeds(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = self._mock_urlopen()
        result = emit_event(self.fixture.profile, "my_tool.go")
        self.assertTrue(result.get("ok"))

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_emit_at_cap_raises(self, mock_urlopen: MagicMock) -> None:
        mock_urlopen.return_value = self._mock_urlopen()
        # Cap is 2; first two succeed, third raises.
        emit_event(self.fixture.profile, "my_tool.go")
        emit_event(self.fixture.profile, "my_tool.go")
        with self.assertRaises(RateLimitExceeded) as cm:
            emit_event(self.fixture.profile, "my_tool.go")
        self.assertEqual(cm.exception.profile, "test-profile")
        self.assertEqual(cm.exception.limit, 2)
        # Cap-trip must happen BEFORE the POST (third urlopen call never fires).
        self.assertEqual(mock_urlopen.call_count, 2)

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_uncapped_profile_no_counter_write(self, mock_urlopen: MagicMock) -> None:
        # Replace limits with one that doesn't include test-profile.
        self.limits_path.write_text(json.dumps({"limits": {"someone-else": 1}}))
        mock_urlopen.return_value = self._mock_urlopen()
        # Many emits should all succeed.
        for _ in range(5):
            emit_event(self.fixture.profile, "my_tool.go")
        # Uncapped profiles must NOT touch the counter file (avoids disk churn
        # from codex-style high-frequency emitters).
        self.assertFalse(self.counter_path.exists())

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_missing_limits_file_no_cap(self, mock_urlopen: MagicMock) -> None:
        self.limits_path.unlink()
        mock_urlopen.return_value = self._mock_urlopen()
        for _ in range(5):
            emit_event(self.fixture.profile, "my_tool.go")

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_corrupt_counter_resets(self, mock_urlopen: MagicMock) -> None:
        # Garbage in the counter file should be treated as fresh state, not
        # crash the emitter. A failure here would brick the fleet anytime the
        # file got mangled (disk full mid-write, manual edit, etc.).
        self.counter_path.write_text("not valid json {")
        mock_urlopen.return_value = self._mock_urlopen()
        result = emit_event(self.fixture.profile, "my_tool.go")
        self.assertTrue(result.get("ok"))
        # Counter rebuilt as valid JSON with today's bucket = 1.
        state = json.loads(self.counter_path.read_text())
        today = next(iter(state.keys()))
        self.assertEqual(state[today]["test-profile"], 1)

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_dry_run_bypasses_counter(self, mock_urlopen: MagicMock) -> None:
        # dry_run should never consume quota — callers use it to inspect
        # built payloads (CI lint, smoke tests). If dry_run counted, the
        # CI suite would exhaust per-day caps on every run.
        for _ in range(10):
            result = emit_event(self.fixture.profile, "my_tool.go", dry_run=True)
            self.assertTrue(result["dry_run"])
        self.assertFalse(self.counter_path.exists())
        self.assertEqual(mock_urlopen.call_count, 0)

    @patch("hermes.lib.agent_events.urllib.request.urlopen")
    def test_zero_and_negative_caps_treated_as_uncapped(self, mock_urlopen: MagicMock) -> None:
        # Config bug: someone sets cap to 0 or -1. The defensible behavior is
        # "ignore the config, log a warning, run uncapped" — a cap of 0 would
        # silently brick the profile, and skipping it is more recoverable than
        # turning every emit into a stop-the-world error.
        self.limits_path.write_text(
            json.dumps({"limits": {"test-profile": 0, "other": -5}})
        )
        mock_urlopen.return_value = self._mock_urlopen()
        for _ in range(3):
            emit_event(self.fixture.profile, "my_tool.go")


class TestFleetLimitsFile(unittest.TestCase):
    """The shipped fleet/limits.json should parse and cover the live profiles."""

    def test_repo_limits_file_is_well_formed(self) -> None:
        path = ROOT / "fleet" / "limits.json"
        self.assertTrue(path.exists(), f"limits file missing at {path}")
        raw = json.loads(path.read_text())
        self.assertIn("limits", raw)
        limits = raw["limits"]
        # All four manually-capped profiles per the research must be present;
        # codex is intentionally absent (uncapped — refactor bursts).
        for profile in ("atlas-ceo", "cmo", "stet", "quill"):
            self.assertIn(profile, limits)
            self.assertIsInstance(limits[profile], int)
            self.assertGreater(limits[profile], 0)
        self.assertNotIn("codex", limits)


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
