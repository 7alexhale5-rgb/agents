"""Tests for the Phase 2 inbox-action + agent-todo writeback helpers.

These complement the existing test_pfos_emit.py which covers the
agent-events writeback path; the new helpers target the per-silo
writeback endpoints PFOS exposes at /api/silos/<slug>/agent-action and
/agent-todo.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pf_runtime.runtime.pfos_emit import (
    _format_silo_url,
    emit_action_sync,
    emit_todo_sync,
    runtime_action_payload,
    runtime_todo_payload,
)

# ---------------------------------------------------------------------------
# runtime_action_payload — shape + action_name + side_effect_class
# ---------------------------------------------------------------------------


def test_action_payload_for_reply_draft() -> None:
    body = runtime_action_payload(
        action_type="reply_draft",
        bucket="needs_reply",
        account_id="gmail-1",
        target_id="msg-abc",
        confidence=0.87,
        rationale="boss asked a question",
        sender="boss@example.com",
        subject="Q3 SOW",
        draft_text="Hi Josh, ...",
    )
    assert body["action_name"] == "inbox.reply_draft"
    assert body["side_effect_class"] == "write"
    assert body["confidence"] == 0.87
    p = body["params_json"]
    assert p["message_id"] == "msg-abc"
    assert p["bucket"] == "needs_reply"
    assert p["sender"] == {"name": "", "address": "boss@example.com"}
    assert p["draft_text"] == "Hi Josh, ..."
    assert p["also_seen_in"] == ["gmail-1"]
    assert "rationale_preview" in p
    assert body["revert_payload_json"] == {"original_state": "proposed"}


def test_action_payload_calendar_hold_uses_calendar_namespace() -> None:
    body = runtime_action_payload(
        action_type="calendar_hold",
        bucket="schedule",
        account_id="gmail-2",
        target_id="msg-xyz",
        confidence=0.91,
    )
    assert body["action_name"] == "calendar.hold"
    assert body["side_effect_class"] == "write"


def test_action_payload_unsubscribe_draft_is_external_side_effect() -> None:
    body = runtime_action_payload(
        action_type="unsubscribe_draft",
        bucket="promotion",
        account_id="gmail-3",
        target_id="msg-promo",
        confidence=0.7,
    )
    assert body["action_name"] == "inbox.unsubscribe_draft"
    assert body["side_effect_class"] == "external"


def test_action_payload_follow_up_task_targets_inbox_namespace() -> None:
    body = runtime_action_payload(
        action_type="follow_up_task",
        bucket="needs_alex_today",
        account_id="koho-m365",
        target_id="msg-urgent",
        confidence=0.92,
        subject="URGENT: please respond",
    )
    assert body["action_name"] == "inbox.follow_up_task"
    assert body["side_effect_class"] == "write"
    assert body["params_json"]["bucket"] == "needs_alex_today"


def test_action_payload_truncates_long_strings() -> None:
    body = runtime_action_payload(
        action_type="reply_draft",
        bucket="needs_reply",
        account_id="gmail-1",
        target_id="msg",
        confidence=0.8,
        subject="x" * 500,
        draft_text="y" * 5000,
        rationale="z" * 1000,
    )
    assert len(body["params_json"]["subject"]) == 280
    assert len(body["params_json"]["draft_text"]) == 2000
    assert len(body["params_json"]["rationale_preview"]) == 500


# ---------------------------------------------------------------------------
# runtime_todo_payload — shape + context linkage + title trim
# ---------------------------------------------------------------------------


def test_todo_payload_minimal() -> None:
    body = runtime_todo_payload(title="  Reply to Josh  ", confidence=0.85)
    assert body["title"] == "Reply to Josh"
    assert body["confidence"] == 0.85
    assert "context" not in body


def test_todo_payload_full_with_context() -> None:
    body = runtime_todo_payload(
        title="Reply to Josh @ Koho",
        confidence=0.9,
        est_minutes=10,
        due_at_iso="2026-05-12T15:00:00Z",
        message_id="msg-abc",
        action_id="action-uuid",
        trace_id="run-1",
    )
    assert body["est_minutes"] == 10
    assert body["due_at"] == "2026-05-12T15:00:00Z"
    assert body["context"] == {"message_id": "msg-abc", "action_id": "action-uuid"}
    assert body["trace_id"] == "run-1"


def test_todo_payload_caps_title_at_300() -> None:
    body = runtime_todo_payload(title="x" * 400, confidence=0.5)
    assert len(body["title"]) == 300


# ---------------------------------------------------------------------------
# _format_silo_url — silo segment substitution
# ---------------------------------------------------------------------------


def test_format_silo_url_swaps_placeholder() -> None:
    template = "https://os.example.com/api/silos/<silo>/agent-action"
    assert (
        _format_silo_url(template, "koho")
        == "https://os.example.com/api/silos/koho/agent-action"
    )


def test_format_silo_url_passthrough_when_no_placeholder() -> None:
    template = "https://os.example.com/api/silos/koho/agent-action"
    assert _format_silo_url(template, "ctox") == template


# ---------------------------------------------------------------------------
# emit_action_sync / emit_todo_sync — env gate + HTTP semantics
# ---------------------------------------------------------------------------


def test_emit_action_sync_noop_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PFOS_INBOX_ACTION_URL", raising=False)
    monkeypatch.delenv("PFOS_INBOX_ACTION_TOKEN", raising=False)
    assert emit_action_sync({"action_name": "inbox.archive"}, silo="koho") is False


def test_emit_todo_sync_noop_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PFOS_INBOX_TODO_URL", raising=False)
    monkeypatch.delenv("PFOS_INBOX_TODO_TOKEN", raising=False)
    assert emit_todo_sync({"title": "x"}, silo="koho") is False


def test_emit_action_sync_posts_to_silo_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PFOS_INBOX_ACTION_URL",
        "https://os.example.com/api/silos/<silo>/agent-action",
    )
    monkeypatch.setenv("PFOS_INBOX_ACTION_TOKEN", "tok")

    captured = {}

    def fake_post(url: str, token: str, body: dict) -> tuple[int, str]:
        captured["url"] = url
        captured["token"] = token
        captured["body"] = body
        return 200, '{"ok":true}'

    with patch("pf_runtime.runtime.pfos_emit._post_json", side_effect=fake_post):
        ok = emit_action_sync({"action_name": "inbox.archive"}, silo="koho")

    assert ok is True
    assert captured["url"] == "https://os.example.com/api/silos/koho/agent-action"
    assert captured["token"] == "tok"
    assert captured["body"] == {"action_name": "inbox.archive"}


def test_emit_todo_sync_returns_false_on_non_2xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "PFOS_INBOX_TODO_URL",
        "https://os.example.com/api/silos/<silo>/agent-todo",
    )
    monkeypatch.setenv("PFOS_INBOX_TODO_TOKEN", "tok")
    with patch(
        "pf_runtime.runtime.pfos_emit._post_json",
        return_value=(503, '{"error":"not_enabled"}'),
    ):
        ok = emit_todo_sync({"title": "x"}, silo="koho")
    assert ok is False


def test_emit_action_sync_rejects_non_http_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PFOS_INBOX_ACTION_URL", "ftp://os.example.com/foo")
    monkeypatch.setenv("PFOS_INBOX_ACTION_TOKEN", "tok")
    with patch("pf_runtime.runtime.pfos_emit._post_json") as post:
        ok = emit_action_sync({"action_name": "inbox.archive"}, silo="koho")
    assert ok is False
    assert post.call_count == 0
