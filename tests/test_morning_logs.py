"""Tests for scripts/morning-logs.py."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "morning-logs.py"

spec = importlib.util.spec_from_file_location("morning_logs_script", SCRIPT)
morning_logs = importlib.util.module_from_spec(spec)
sys.modules["morning_logs_script"] = morning_logs
spec.loader.exec_module(morning_logs)


class TestMorningLogsSummary(unittest.TestCase):
    def test_summarize_healthy_gateway_with_approvals(self) -> None:
        snapshot = {
            "dashboard": {"status": {"value": {"gateway_running": True}}},
            "fleet": {
                "ops": {"value": {"gateway_state": "running", "gateway_running": True, "platforms": {}}},
                "approvals": {
                    "value": {
                        "approvals": [
                            {"agent_slug": "marin", "skill_slug": "weekly-review", "age_hours": 3, "type": "x"},
                            {"agent_slug": "stet", "skill_slug": "critique", "age_hours": 9, "type": "y"},
                        ]
                    }
                },
                "events": {"value": {"events": [{"id": "1"}]}},
            },
            "labyrinth": {
                "health": {"value": {"ok": True}},
                "guideposts": {"value": {"guideposts": []}},
            },
            "runtime": {"logs": {"agent": {"error_count": 0}, "gateway": {"error_count": 0}}},
            "repos": [{"name": "agents", "dirty_count": 0}],
        }
        summary = morning_logs.summarize(snapshot)
        self.assertTrue(summary["usable"])
        self.assertEqual(summary["approval_count"], 2)
        self.assertIn("stet", summary["recommended_next_action"])

    def test_summarize_gateway_down_is_not_usable(self) -> None:
        snapshot = {
            "dashboard": {"status": {"value": {"gateway_running": False}}},
            "fleet": {
                "ops": {"value": {"gateway_state": "startup_failed", "gateway_running": False, "platforms": {}}},
                "approvals": {"value": {"approvals": []}},
                "events": {"value": {"events": []}},
            },
            "labyrinth": {
                "health": {"value": {"ok": True}},
                "guideposts": {"value": {"guideposts": []}},
            },
            "runtime": {"logs": {}},
            "repos": [],
        }
        summary = morning_logs.summarize(snapshot)
        self.assertFalse(summary["usable"])
        self.assertIn("gateway not running", summary["broken"])

    def test_redact_common_tokens(self) -> None:
        text = "Authorization: Bearer sk-test1234567890 and SLACK_TOKEN=xoxb-123456789012"
        redacted = morning_logs.redact(text)
        self.assertNotIn("sk-test", redacted)
        self.assertNotIn("xoxb-", redacted)

    def test_load_event_env_accepts_export_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / "hermes-tokens.env"
            env_file.write_text(
                "export HERMES_AGENT_EVENTS_TOKEN=fake-token\n"
                "export HERMES_AGENT_EVENTS_URL=https://example.test\n"
            )
            with patch.object(morning_logs, "TOKEN_ENV", env_file), patch.dict(morning_logs.os.environ, {}, clear=True):
                morning_logs.load_event_env()
                self.assertEqual(morning_logs.os.environ["HERMES_AGENT_EVENTS_TOKEN"], "fake-token")
                self.assertEqual(morning_logs.os.environ["HERMES_AGENT_EVENTS_URL"], "https://example.test")


if __name__ == "__main__":
    unittest.main(verbosity=2)
