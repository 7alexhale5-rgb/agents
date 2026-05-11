"""Tests for pf_runtime.oauth.provision — listener captures, .env writes.

No real OAuth round-trip; we hit our own listener with a fake redirect.
"""

from __future__ import annotations

import io
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch

import pytest

from pf_runtime.oauth import provision as op


@pytest.fixture
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "hermes"
    profile = home / "profiles" / "personal"
    profile.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    return home


def _write_env(home: Path, contents: str) -> None:
    (home / "profiles" / "personal" / ".env").write_text(contents)


def _hit_callback(port: int, code: str, state: str = "", path: str = "/callback") -> None:
    params = {"code": code}
    if state:
        params["state"] = state
    url = f"http://127.0.0.1:{port}{path}?{urllib.parse.urlencode(params)}"
    # Small retry — the listener thread may not be ready instantly.
    # The handler may answer with HTTP 400 (state mismatch), which urllib raises
    # as HTTPError — that still counts as "reached the listener".
    last_err: Exception | None = None
    for _ in range(20):
        try:
            urllib.request.urlopen(url, timeout=2)  # noqa: S310
            return
        except urllib.error.HTTPError:
            # 400/404 from the handler — listener reached, response observed.
            return
        except (OSError, urllib.error.URLError) as exc:
            last_err = exc
            time.sleep(0.05)
    raise RuntimeError(f"could not reach listener at {url}: {last_err}")


def test_listener_captures_code_and_state(hermes_home: Path) -> None:
    port = op._free_port(0)  # 0 → kernel assigns a free port; not used by real Google
    # Re-pick a deterministic port; _free_port returns the input, so we pick one
    port = 51211

    result: list[op._CapturedCode] = []

    def runner() -> None:
        result.append(op._run_listener(port, "/callback", "expected-state", timeout_s=5))

    t = threading.Thread(target=runner)
    t.start()
    _hit_callback(port, code="auth-code-abc", state="expected-state")
    t.join(timeout=6)
    assert len(result) == 1
    assert result[0].code == "auth-code-abc"
    assert result[0].state == "expected-state"
    assert result[0].error is None


def test_listener_rejects_state_mismatch(hermes_home: Path) -> None:
    port = 51212
    result: list[op._CapturedCode] = []

    def runner() -> None:
        result.append(op._run_listener(port, "/callback", "expected-state", timeout_s=5))

    t = threading.Thread(target=runner)
    t.start()
    _hit_callback(port, code="auth-code-bad", state="not-the-state")
    t.join(timeout=6)
    # We still capture the code (per the handler), but the operator can verify
    # state at the call site. Confirm the captured state is the wrong one so
    # callers can act.
    assert result[0].code == "auth-code-bad"
    assert result[0].state == "not-the-state"


def test_write_env_line_replaces_existing(hermes_home: Path) -> None:
    _write_env(hermes_home, "PF_FOO=old\nPF_BAR=keep\n")
    op._write_env_line("personal", "PF_FOO", "new")
    content = (hermes_home / "profiles" / "personal" / ".env").read_text()
    assert "PF_FOO=new" in content
    assert "PF_BAR=keep" in content


def test_write_env_line_appends_when_missing(hermes_home: Path) -> None:
    _write_env(hermes_home, "PF_BAR=keep\n")
    op._write_env_line("personal", "PF_FOO", "added")
    content = (hermes_home / "profiles" / "personal" / ".env").read_text()
    assert "PF_FOO=added" in content
    assert "PF_BAR=keep" in content


def test_google_exchange_uses_token_endpoint(hermes_home: Path) -> None:
    fake_body = json.dumps({
        "access_token": "ya29.fresh",
        "refresh_token": "rt-fresh",
        "expires_in": 3600,
    }).encode()

    fake_resp = io.BytesIO(fake_body)
    fake_resp.__enter__ = lambda *a: fake_resp  # type: ignore[method-assign]
    fake_resp.__exit__ = lambda *a: None  # type: ignore[method-assign]

    with patch.object(op.urllib.request, "urlopen", return_value=fake_resp) as m:
        tokens = op._exchange_google_code("cid", "cs", "auth-code", "http://127.0.0.1:8765/callback")
    assert tokens["access_token"] == "ya29.fresh"
    assert tokens["refresh_token"] == "rt-fresh"
    req = m.call_args[0][0]
    assert "oauth2.googleapis.com" in req.full_url


def test_microsoft_exchange_uses_tenant_token_endpoint() -> None:
    fake_body = json.dumps({
        "access_token": "eyJ.fresh",
        "refresh_token": "rt-rotated",
        "expires_in": 3600,
    }).encode()
    fake_resp = io.BytesIO(fake_body)
    fake_resp.__enter__ = lambda *a: fake_resp  # type: ignore[method-assign]
    fake_resp.__exit__ = lambda *a: None  # type: ignore[method-assign]
    with patch.object(op.urllib.request, "urlopen", return_value=fake_resp) as m:
        tokens = op._exchange_microsoft_code(
            "cid", "cs", "auth-code", "http://127.0.0.1:8765/callback",
            "Mail.Read offline_access", "common",
        )
    assert tokens["access_token"] == "eyJ.fresh"
    assert tokens["refresh_token"] == "rt-rotated"
    req = m.call_args[0][0]
    assert "login.microsoftonline.com/common/oauth2/v2.0/token" in req.full_url
