from __future__ import annotations

import base64
import inspect
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hermes.lib import gmail_drafts  # noqa: E402


class _FakeCreate:
    def __init__(self, response):
        self.response = response

    def execute(self):
        return self.response


class _FakeDrafts:
    def __init__(self):
        self.calls = []

    def create(self, *, userId, body):
        self.calls.append({"userId": userId, "body": body})
        return _FakeCreate(
            {
                "id": "draft-123",
                "message": {"id": "msg-123", "threadId": "thread-123"},
            }
        )


class _FakeUsers:
    def __init__(self, drafts):
        self._drafts = drafts

    def drafts(self):
        return self._drafts


class _FakeGmailService:
    def __init__(self):
        self.drafts_resource = _FakeDrafts()

    def users(self):
        return _FakeUsers(self.drafts_resource)


class GmailDraftTests(unittest.TestCase):
    def test_raw_message_is_base64url_encoded_mime(self) -> None:
        raw = gmail_drafts._raw_message(
            to="alex@prettyflyforai.com",
            subject="Pilot draft",
            body_text="Plain text body.",
        )

        decoded = base64.urlsafe_b64decode(raw.encode("ascii")).decode("utf-8")
        self.assertIn("To: alex@prettyflyforai.com", decoded)
        self.assertIn("Subject: Pilot draft", decoded)
        self.assertIn("Plain text body.", decoded)

    def test_create_draft_calls_gmail_drafts_create(self) -> None:
        service = _FakeGmailService()
        profile_dir = ROOT / "hermes" / "profiles" / "marin"

        with patch("hermes.lib.gmail_drafts.emit_event") as emit:
            emit.return_value = {"dry_run": True, "payload": {"type": "marin.gmail_draft.proposed"}}
            result = gmail_drafts.create_draft(
                profile_dir,
                to="Alex@PrettyFlyForAI.com",
                subject="Pilot draft",
                body_text="Plain text body.",
                target_account="alex@prettyflyforai.com",
                service=service,
                dry_run_event=True,
            )

        self.assertEqual(len(service.drafts_resource.calls), 1)
        call = service.drafts_resource.calls[0]
        self.assertEqual(call["userId"], "me")
        self.assertIn("raw", call["body"]["message"])
        self.assertEqual(result["draft"]["draft_id"], "draft-123")
        self.assertEqual(result["draft"]["message_id"], "msg-123")
        self.assertEqual(result["draft"]["thread_id"], "thread-123")
        self.assertEqual(len(result["draft"]["recipient_hash"]), 16)
        self.assertEqual(len(result["draft"]["target_account_hash"]), 16)
        emitted_data = emit.call_args.kwargs["overrides"]["data"]
        self.assertEqual(emitted_data["gmail_endpoint"], "users.drafts.create")
        self.assertNotIn("Plain text body.", str(emitted_data))
        self.assertNotIn("Alex@PrettyFlyForAI.com", str(emitted_data))

    def test_adapter_has_no_send_surface(self) -> None:
        source = inspect.getsource(gmail_drafts)
        self.assertNotIn("messages().send", source)
        self.assertNotIn("drafts().send", source)

    def test_marin_config_exposes_draft_tool_and_forbids_sends(self) -> None:
        cfg_path = ROOT / "hermes" / "profiles" / "marin" / "config.yaml"
        cfg = yaml.safe_load(cfg_path.read_text())

        self.assertIn("marin.gmail_create_draft", cfg["tools"]["builtin"])
        contract = cfg["tools"]["contracts"]["marin.gmail_create_draft"]
        self.assertEqual(contract["authority"], "proposed_write_only")
        self.assertEqual(contract["event"]["type"], "marin.gmail_draft.proposed")
        self.assertTrue(cfg["guardrails"]["forbid_external_sends"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
