"""Communications provider normalization and policy tests."""
from __future__ import annotations

from email.message import EmailMessage
from pathlib import Path

import pytest

from pf_runtime.communications import (
    AccountConfig,
    MutationNotAllowedError,
    ProposalStore,
    ProposedAction,
)
from pf_runtime.communications.policy import assert_v1_action_allowed
from pf_runtime.communications.providers import (
    normalize_gmail_message,
    normalize_graph_message,
    normalize_imap_message,
)
from pf_runtime.communications.schema import ActionType, Provider


def test_gmail_message_normalizes_to_common_schema() -> None:
    account = AccountConfig(
        account_id="gmail-1",
        provider=Provider.GOOGLE_MAIL,
        address="alex@example.com",
        scopes=("https://www.googleapis.com/auth/gmail.readonly",),
    )
    raw = {
        "id": "gm-1",
        "threadId": "th-1",
        "snippet": "Quick update",
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [
                {"name": "From", "value": "Dana <dana@example.com>"},
                {"name": "To", "value": "Alex <alex@example.com>"},
                {"name": "Subject", "value": "Contract question"},
                {"name": "Date", "value": "2026-05-08T12:00:00Z"},
            ],
            "parts": [
                {
                    "filename": "terms.pdf",
                    "mimeType": "application/pdf",
                    "body": {"attachmentId": "att-1", "size": 42},
                }
            ],
        },
    }
    msg = normalize_gmail_message(account, raw)
    assert msg.provider == Provider.GOOGLE_MAIL
    assert msg.message_id == "gm-1"
    assert msg.thread_id == "th-1"
    assert msg.sender == "dana@example.com"
    assert msg.recipients == ("alex@example.com",)
    assert msg.attachments_meta[0].provider_id == "att-1"


def test_graph_message_normalizes_to_common_schema() -> None:
    account = AccountConfig(
        account_id="koho",
        provider=Provider.MICROSOFT_GRAPH,
        address="alex@kohoconsulting.com",
        scopes=("Mail.Read", "Calendars.ReadBasic"),
    )
    raw = {
        "id": "g-1",
        "conversationId": "conv-1",
        "sender": {"emailAddress": {"address": "client@example.com"}},
        "toRecipients": [{"emailAddress": {"address": "alex@kohoconsulting.com"}}],
        "subject": "Kickoff",
        "receivedDateTime": "2026-05-08T13:00:00Z",
        "bodyPreview": "Can we meet tomorrow?",
        "attachments": [{"id": "a1", "name": "brief.docx", "size": 10}],
    }
    msg = normalize_graph_message(account, raw)
    assert msg.provider == Provider.MICROSOFT_GRAPH
    assert msg.sender == "client@example.com"
    assert msg.provider_ids["graph_conversation_id"] == "conv-1"


def test_imap_message_normalizes_to_common_schema() -> None:
    account = AccountConfig(
        account_id="yeh",
        provider=Provider.IMAP_HOSTGATOR,
        address="alex@yehovahbuilders.com",
    )
    raw = EmailMessage()
    raw["From"] = "Builder <ops@yehovahbuilders.com>"
    raw["To"] = "Alex <alex@yehovahbuilders.com>"
    raw["Subject"] = "Permit update"
    raw["Date"] = "Fri, 08 May 2026 09:00:00 -0500"
    raw["Message-ID"] = "<m1@example.com>"
    raw.set_content("Permit packet is ready.")
    msg = normalize_imap_message(account, raw, uid="44")
    assert msg.provider == Provider.IMAP_HOSTGATOR
    assert msg.message_id == "44"
    assert msg.sender == "ops@yehovahbuilders.com"
    assert "Permit packet" in msg.snippet


def test_v1_policy_refuses_live_mutation() -> None:
    action = ProposedAction(
        action_id="p1",
        action_type=ActionType.TRASH,
        account_id="gmail-1",
        target_id="gm-1",
        rationale="obvious noise",
    )
    assert_v1_action_allowed(action, applying=False)
    with pytest.raises(MutationNotAllowedError):
        assert_v1_action_allowed(action, applying=True)


def test_proposal_store_round_trip(tmp_path: Path) -> None:
    store = ProposalStore(tmp_path / "proposals.sqlite")
    action = ProposedAction(
        action_id="p1",
        action_type=ActionType.REPLY_DRAFT,
        account_id="koho",
        target_id="g-1",
        rationale="client needs a reply",
        payload={"draft": "I'll follow up today."},
    )
    assert store.add(action) == "p1"
    rows = store.list()
    assert len(rows) == 1
    assert rows[0].payload["draft"] == "I'll follow up today."
    store.mark_reviewed("p1", status="approved")
    assert store.list() == []
