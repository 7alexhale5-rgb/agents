"""Tests for env-gated PFOS agent-event client."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from io import BytesIO
from unittest.mock import patch

import pytest

from pf_runtime.runtime.pfos_emit import (
    emit_agent_event,
    emit_agent_event_sync,
    is_configured,
    runtime_proposal_payload,
    runtime_reply_payload,
)


@pytest.fixture
def clear_pfos_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PFOS_AGENT_EVENT_URL", raising=False)
    monkeypatch.delenv("PFOS_AGENT_EVENT_TOKEN", raising=False)
    monkeypatch.delenv("PFOS_AGENT_EVENT_REQUIRE_HTTPS", raising=False)
    monkeypatch.delenv("PFOS_JOURNAL_EVENT_MIRROR", raising=False)
    monkeypatch.delenv("PFOS_JOURNAL_SERVICE", raising=False)


def test_is_configured_false_when_missing(clear_pfos_env: None) -> None:
    assert is_configured() is False


def test_is_configured_true_when_both_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PFOS_AGENT_EVENT_URL", "https://os.example/api/silos/fleet/agent-event")
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "secret")
    assert is_configured() is True


def test_emit_sync_no_op_when_not_configured(
    clear_pfos_env: None,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level("WARNING")
    assert emit_agent_event_sync({"type": "X", "data": {}}) is False
    assert not caplog.records
    assert capsys.readouterr().out == ""


def test_emit_sync_posts_json_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "PFOS_AGENT_EVENT_URL",
        "https://os.example/api/silos/fleet/agent-event",
    )
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")

    captured: dict[str, object] = {}

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b'{"ok":true}'

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

    def fake_urlopen(
        req: urllib.request.Request,
        timeout: float | None = None,
    ) -> _Resp:
        captured["method"] = req.get_method()
        captured["full_url"] = req.full_url
        captured["headers"] = dict(req.header_items())
        captured["data"] = req.data
        return _Resp()

    with patch("pf_runtime.runtime.pfos_emit.urllib.request.urlopen", fake_urlopen):
        ok = emit_agent_event_sync({"type": "STATE_CHANGED", "data": {"k": 1}})

    assert ok is True
    assert captured["method"] == "POST"
    assert captured["full_url"] == "https://os.example/api/silos/fleet/agent-event"
    headers = {k.lower(): v for k, v in captured["headers"].items()}
    assert headers["authorization"] == "Bearer tok"
    assert headers["content-type"] == "application/json"
    body = json.loads(captured["data"].decode("utf-8"))
    assert body == {"type": "STATE_CHANGED", "data": {"k": 1}}


def test_emit_sync_mirrors_journal_event_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv(
        "PFOS_AGENT_EVENT_URL",
        "https://os.example/api/silos/fleet/agent-event",
    )
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")
    monkeypatch.setenv("PFOS_JOURNAL_EVENT_MIRROR", "1")
    monkeypatch.setenv("PFOS_JOURNAL_SERVICE", "atlas-runtime")

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

    def _open(*_a: object, **_k: object) -> _Resp:
        return _Resp()

    payload = runtime_proposal_payload(
        profile_slug="atlas-ceo",
        skill_slug="gmail:gmail-inbox-triage",
        agent_slug="atlas-ceo",
        action_id="act-1",
        action_type="archive",
        account_id="acct-1",
        target_id="msg-1",
        rationale_preview="routine newsletter",
        trace_id="trace-1",
        parent_run_id="123e4567-e89b-12d3-a456-426614174000",
    )

    with patch("pf_runtime.runtime.pfos_emit.urllib.request.urlopen", _open):
        assert emit_agent_event_sync(payload) is True

    line = capsys.readouterr().out.strip()
    mirrored = json.loads(line)
    assert mirrored["event"] == "agent_event"
    assert mirrored["service"] == "atlas-runtime"
    assert mirrored["agent_slug"] == "atlas-ceo"
    assert mirrored["type"] == "ARTIFACT_CREATED"
    assert mirrored["status"] == "pending"
    assert mirrored["surface"] == "pf_runtime"
    assert mirrored["cwd_project"] == "atlas-ceo"
    assert mirrored["skill_slug"] == "gmail:gmail-inbox-triage"
    assert mirrored["parent_run_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert mirrored["trace_id"] == "trace-1"
    assert mirrored["data"]["kind"] == "pf_runtime_proposal"


def test_journal_mirror_defaults_agent_slug_from_cwd_project(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("PFOS_AGENT_EVENT_URL", "https://os.example/e")
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")
    monkeypatch.setenv("PFOS_JOURNAL_EVENT_MIRROR", "1")
    monkeypatch.setenv("PFOS_JOURNAL_SERVICE", "atlas-runtime")

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

    with patch("pf_runtime.runtime.pfos_emit.urllib.request.urlopen", return_value=_Resp()):
        assert emit_agent_event_sync(
            {
                "type": "STATE_CHANGED",
                "data": {},
                "surface": "pf_runtime",
                "cwd_project": "atlas-ceo",
            },
        )

    mirrored = json.loads(capsys.readouterr().out.strip())
    assert mirrored["service"] == "atlas-runtime"
    assert mirrored["agent_slug"] == "atlas-ceo"


def test_journal_mirror_never_breaks_direct_emit(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv(
        "PFOS_AGENT_EVENT_URL",
        "https://os.example/api/silos/fleet/agent-event",
    )
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")
    monkeypatch.setenv("PFOS_JOURNAL_EVENT_MIRROR", "1")
    caplog.set_level("WARNING")

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

    with (
        patch("sys.stdout.write", side_effect=OSError("stdout closed")),
        patch("pf_runtime.runtime.pfos_emit.urllib.request.urlopen", return_value=_Resp()),
    ):
        assert emit_agent_event_sync({"type": "STATE_CHANGED", "data": {}}) is True

    assert any("journal mirror failed" in r.message for r in caplog.records)


def test_emit_sync_rejects_http_when_require_https(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("PFOS_AGENT_EVENT_URL", "http://os.example/e")
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")
    monkeypatch.setenv("PFOS_AGENT_EVENT_REQUIRE_HTTPS", "1")
    caplog.set_level("WARNING")
    assert emit_agent_event_sync({"type": "T", "data": {}}) is False
    assert any("https" in r.message.lower() for r in caplog.records)


def test_emit_sync_allows_http_when_require_https_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PFOS_AGENT_EVENT_URL", "http://os.example/e")
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")

    class _Resp:
        status = 200

        def read(self) -> bytes:
            return b"{}"

        def __enter__(self) -> _Resp:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

    def _open(*_a: object, **_k: object) -> _Resp:
        return _Resp()

    with patch("pf_runtime.runtime.pfos_emit.urllib.request.urlopen", _open):
        assert emit_agent_event_sync({"type": "STATE_CHANGED", "data": {}}) is True


def test_emit_sync_false_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PFOS_AGENT_EVENT_URL", "https://os.example/e")
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")

    err = urllib.error.HTTPError("url", 503, "err", hdrs=None, fp=BytesIO(b"{}"))
    with patch("pf_runtime.runtime.pfos_emit.urllib.request.urlopen", side_effect=err):
        assert emit_agent_event_sync({"type": "T", "data": {}}) is False


@pytest.mark.asyncio
async def test_emit_async_delegates_to_sync(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PFOS_AGENT_EVENT_URL", "https://os.example/e")
    monkeypatch.setenv("PFOS_AGENT_EVENT_TOKEN", "tok")

    with patch(
        "pf_runtime.runtime.pfos_emit.emit_agent_event_sync",
        return_value=True,
    ) as m:
        ok = await emit_agent_event({"type": "T", "data": {}})

    assert ok is True
    m.assert_called_once_with({"type": "T", "data": {}})


def test_runtime_reply_payload_shape() -> None:
    p = runtime_reply_payload(
        channel="slack",
        profile_slug="personal",
        text_preview="hello world",
        session_id="sid-1",
        inbound_preview="user said hi",
    )
    assert p["type"] == "STATE_CHANGED"
    assert p["agent_slug"] == "personal"
    assert p["surface"] == "pf_runtime"
    assert p["cwd_project"] == "personal"
    d = p["data"]
    assert d["kind"] == "pf_runtime_reply"
    assert d["channel"] == "slack"
    assert d["text_preview"] == "hello world"
    assert d["session_id"] == "sid-1"
    assert d["inbound_preview"] == "user said hi"
    assert "trace_id" not in p


def test_runtime_reply_payload_truncates_long_text() -> None:
    long = "x" * 5000
    p = runtime_reply_payload(
        channel="slack",
        profile_slug="p",
        text_preview=long,
    )
    assert len(p["data"]["text_preview"]) == 2000
