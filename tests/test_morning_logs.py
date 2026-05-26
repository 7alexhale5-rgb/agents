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


def healthy_knowledge_vault() -> dict:
    return {
        "status": {
            "ok": True,
            "value": {
                "freshness": {
                    "ok": True,
                    "failures": [],
                    "warnings": [],
                }
            },
        },
        "retrieval": {
            "ok": True,
            "value": {"ok": True, "passed": 10, "total": 10, "failed": 0},
        },
        "memory_health": {
            "ok": True,
            "value": {
                "snapshot": {
                    "verdict": "usable",
                    "warnings_count": 0,
                    "blockers_count": 0,
                    "strict_wiki_blockers": [],
                }
            },
        },
    }


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
            "knowledge_vault": healthy_knowledge_vault(),
            "runtime": {"logs": {"agent": {"error_count": 0}, "gateway": {"error_count": 0}}},
            "repos": [{"name": "agents", "dirty_count": 0}],
        }
        summary = morning_logs.summarize(snapshot)
        self.assertTrue(summary["usable"])
        self.assertTrue(summary["memory_trustworthy"])
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
            "knowledge_vault": healthy_knowledge_vault(),
            "runtime": {"logs": {}},
            "repos": [],
        }
        summary = morning_logs.summarize(snapshot)
        self.assertFalse(summary["usable"])
        self.assertIn("gateway not running", summary["broken"])

    def test_summarize_stale_freshness_warning_keeps_memory_trustworthy(self) -> None:
        knowledge = healthy_knowledge_vault()
        knowledge["status"]["value"]["freshness"]["warnings"] = ["obsidian index is stale (1h-24h old)"]
        snapshot = {
            "dashboard": {"status": {"value": {"gateway_running": True}}},
            "fleet": {
                "ops": {"value": {"gateway_state": "running", "gateway_running": True, "platforms": {}}},
                "approvals": {"value": {"approvals": []}},
                "events": {"value": {"events": []}},
            },
            "labyrinth": {
                "health": {"value": {"ok": True}},
                "guideposts": {"value": {"guideposts": []}},
            },
            "knowledge_vault": knowledge,
            "runtime": {"logs": {"agent": {"error_count": 0}, "gateway": {"error_count": 0}}},
            "repos": [],
        }
        summary = morning_logs.summarize(snapshot)
        self.assertTrue(summary["memory_trustworthy"])
        self.assertEqual(summary["freshness_warning_count"], 1)
        self.assertEqual(summary["recommended_next_action"], "Hermes is usable; continue with the morning operating loop.")

    def test_summarize_ignores_remediated_morning_logs_guideposts(self) -> None:
        snapshot = {
            "generated_at": "2026-05-24T15:00:00+00:00",
            "dashboard": {"status": {"value": {"gateway_running": True}}},
            "fleet": {
                "ops": {"value": {"gateway_state": "running", "gateway_running": True, "platforms": {}}},
                "approvals": {"value": {"approvals": []}},
                "events": {"value": {"events": []}},
            },
            "labyrinth": {
                "health": {"value": {"ok": True}},
                "guideposts": {
                    "value": {
                        "guideposts": [
                            {
                                "severity": "warning",
                                "kind": "failure",
                                "journey_id": "cron_25b6aa2097cf_20260524_080043",
                                "title": "6 failed crossing(s)",
                            },
                            {
                                "severity": "warning",
                                "kind": "loop",
                                "journey_id": "cron_25b6aa2097cf_20260523_080000",
                                "title": "Repeated failing tool: agent",
                            },
                            {
                                "severity": "warning",
                                "kind": "failure",
                                "journey_id": "20260507_122502_2fcbc5c8",
                                "title": "15 failed crossing(s)",
                            },
                        ]
                    }
                },
            },
            "knowledge_vault": healthy_knowledge_vault(),
            "runtime": {"logs": {"agent": {"error_count": 0}, "gateway": {"error_count": 0}}},
            "repos": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            jobs = Path(tmp) / "cron" / "jobs.json"
            jobs.parent.mkdir(parents=True)
            jobs.write_text(
                '{"jobs":[{"id":"25b6aa2097cf","no_agent":true,'
                '"script":"morning-logs.sh","last_status":"ok"}]}'
            )
            with patch.object(morning_logs, "HERMES_PROFILE_HOME", Path(tmp)):
                summary = morning_logs.summarize(snapshot)

        self.assertEqual(summary["guidepost_warning_count"], 0)
        self.assertNotIn("Labyrinth warning/error", " ".join(summary["broken"]))
        self.assertEqual(
            summary["recommended_next_action"],
            "Hermes is usable; continue with the morning operating loop.",
        )

    def test_summarize_keeps_current_unremediated_guideposts_actionable(self) -> None:
        snapshot = {
            "generated_at": "2026-05-24T15:00:00+00:00",
            "dashboard": {"status": {"value": {"gateway_running": True}}},
            "fleet": {
                "ops": {"value": {"gateway_state": "running", "gateway_running": True, "platforms": {}}},
                "approvals": {"value": {"approvals": []}},
                "events": {"value": {"events": []}},
            },
            "labyrinth": {
                "health": {"value": {"ok": True}},
                "guideposts": {
                    "value": {
                        "guideposts": [
                            {
                                "severity": "warning",
                                "kind": "failure",
                                "journey_id": "20260524_122502_2fcbc5c8",
                                "title": "2 failed crossing(s)",
                            }
                        ]
                    }
                },
            },
            "knowledge_vault": healthy_knowledge_vault(),
            "runtime": {"logs": {"agent": {"error_count": 0}, "gateway": {"error_count": 0}}},
            "repos": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(morning_logs, "HERMES_PROFILE_HOME", Path(tmp)):
                summary = morning_logs.summarize(snapshot)

        self.assertEqual(summary["guidepost_warning_count"], 1)
        self.assertIn("1 Labyrinth warning/error guidepost(s)", summary["broken"])
        self.assertEqual(summary["recommended_next_action"], "Open Labyrinth guideposts and inspect the warning journey.")

    def test_summarize_memory_health_blockers_break_memory_trust(self) -> None:
        knowledge = healthy_knowledge_vault()
        knowledge["memory_health"]["value"]["snapshot"] = {
            "verdict": "needs attention",
            "warnings_count": 4,
            "blockers_count": 3,
            "strict_wiki_blockers": [
                "wiki/graph-health.md: source newer than last_compiled: memory-command-center.md",
                "credentials/raw-secret.md",
            ],
        }
        snapshot = {
            "dashboard": {"status": {"value": {"gateway_running": True}}},
            "fleet": {
                "ops": {"value": {"gateway_state": "running", "gateway_running": True, "platforms": {}}},
                "approvals": {"value": {"approvals": []}},
                "events": {"value": {"events": []}},
            },
            "labyrinth": {
                "health": {"value": {"ok": True}},
                "guideposts": {"value": {"guideposts": []}},
            },
            "knowledge_vault": knowledge,
            "runtime": {"logs": {"agent": {"error_count": 0}, "gateway": {"error_count": 0}}},
            "repos": [],
        }
        summary = morning_logs.summarize(snapshot)
        self.assertFalse(summary["memory_trustworthy"])
        self.assertEqual(summary["memory_blockers_count"], 3)
        self.assertIn("Memory health has 3 blocker(s)", summary["broken"])
        self.assertNotIn("credentials", " ".join(summary["strict_wiki_blockers"]).lower())
        self.assertEqual(
            summary["recommended_next_action"],
            "Open Knowledge Vault memory health and review blockers before trusting memory.",
        )

    def test_emit_summary_keeps_knowledge_fields_compact(self) -> None:
        summary = {
            "usable": True,
            "gateway_state": "running",
            "approval_count": 0,
            "guidepost_warning_count": 0,
            "dirty_repo_count": 0,
            "log_error_count": 0,
            "memory_trustworthy": False,
            "freshness_ok": True,
            "retrieval_ok": True,
            "retrieval_passed": 10,
            "retrieval_total": 10,
            "memory_health_verdict": "needs attention",
            "memory_blockers_count": 3,
            "memory_warnings_count": 4,
            "api_usage_available": True,
            "api_usage_today_usd": 12.34,
            "api_usage_mtd_usd": 56.78,
            "api_usage_warning_count": 0,
            "api_usage_manual_review_overdue_count": 0,
            "recommended_next_action": "Open Knowledge Vault memory health.",
        }
        with (
            patch.object(morning_logs, "load_event_env"),
            patch.object(morning_logs, "emit_event", return_value={"dry_run": True}) as emit,
        ):
            morning_logs.emit_summary(
                summary,
                morning_logs.ROOT / "_inbox" / "morning-logs" / "2026-05-22-morning-logs.md",
                dry_run=True,
            )
        event_data = emit.call_args.args[2]["data"]
        self.assertEqual(event_data["memory_health_verdict"], "needs attention")
        self.assertEqual(event_data["memory_blockers_count"], 3)
        self.assertEqual(event_data["knowledge_retrieval_passed"], 10)
        self.assertNotIn("strict_wiki_blockers", event_data)
        self.assertNotIn("raw", "".join(event_data.keys()).lower())

    def test_redact_common_tokens(self) -> None:
        text = (
            "Authorization: Bearer "
            + "sk-test"
            + "1234567890 and SLACK_TOKEN="
            + "xoxb-"
            + "123456789012"
        )
        redacted = morning_logs.redact(text)
        self.assertNotIn("sk-test", redacted)
        self.assertNotIn("xoxb-", redacted)

    def test_api_usage_default_path_is_operator_home_not_profile_home(self) -> None:
        self.assertEqual(
            morning_logs.API_USAGE_LATEST,
            Path("/Users/alexhale/.api-usage/latest.json"),
        )

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
