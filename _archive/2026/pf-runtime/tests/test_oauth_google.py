"""Tests for pf_runtime.oauth.google — no network calls.

Mocks urllib.request.urlopen so we never hit oauth2.googleapis.com.
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pf_runtime.oauth import google as og


@pytest.fixture
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "hermes"
    profile = home / "profiles" / "personal"
    profile.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    monkeypatch.delenv("PF_GOOGLE_OAUTH_CLIENT_ID", raising=False)
    monkeypatch.delenv("PF_GOOGLE_OAUTH_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("PF_GMAIL_REFRESH_TOKEN_GMAIL_1", raising=False)
    monkeypatch.delenv("PF_GMAIL_TOKEN_GMAIL_1", raising=False)
    return home


def _write_env(home: Path, contents: str) -> None:
    (home / "profiles" / "personal" / ".env").write_text(contents)


def _fake_token_response(access_token: str = "ya29.new", expires_in: int = 3600) -> io.BytesIO:
    body = json.dumps({"access_token": access_token, "expires_in": expires_in, "token_type": "Bearer"}).encode()
    resp = io.BytesIO(body)
    resp.__enter__ = lambda *a: resp  # type: ignore[method-assign]
    resp.__exit__ = lambda *a: None   # type: ignore[method-assign]
    return resp


def test_env_key_uppercase_underscore() -> None:
    assert og._env_key("gmail-1") == "PF_GMAIL_REFRESH_TOKEN_GMAIL_1"
    assert og._access_token_env_key("gmail-2-calendar") == "PF_GMAIL_TOKEN_GMAIL_2_CALENDAR"


def test_from_env_missing_vars_raises(hermes_home: Path) -> None:
    _write_env(hermes_home, "")
    with pytest.raises(ValueError, match="missing env vars"):
        og.RefreshableGoogleCredentials.from_env("gmail-1", profile="personal")


def test_from_env_loads_from_profile_env(hermes_home: Path) -> None:
    _write_env(hermes_home, (
        "PF_GOOGLE_OAUTH_CLIENT_ID=cid-123\n"
        "PF_GOOGLE_OAUTH_CLIENT_SECRET=secret-abc\n"
        "PF_GMAIL_REFRESH_TOKEN_GMAIL_1=rt-xyz\n"
    ))
    creds = og.RefreshableGoogleCredentials.from_env("gmail-1", profile="personal")
    assert creds.client_id == "cid-123"
    assert creds.client_secret == "secret-abc"
    assert creds.refresh_token == "rt-xyz"


def test_refresh_writes_cache(hermes_home: Path) -> None:
    _write_env(hermes_home, (
        "PF_GOOGLE_OAUTH_CLIENT_ID=cid\n"
        "PF_GOOGLE_OAUTH_CLIENT_SECRET=cs\n"
        "PF_GMAIL_REFRESH_TOKEN_GMAIL_1=rt\n"
    ))
    creds = og.RefreshableGoogleCredentials.from_env("gmail-1", profile="personal")
    with patch.object(og.urllib.request, "urlopen", return_value=_fake_token_response("ya29.fresh", 3600)):
        record = creds.refresh()
    assert record["access_token"] == "ya29.fresh"
    cache = og._read_cache("personal", "gmail-1")
    assert cache is not None
    assert cache["access_token"] == "ya29.fresh"
    assert cache["expires_at"] > time.time()


def test_get_access_token_uses_cache_when_fresh(hermes_home: Path) -> None:
    _write_env(hermes_home, (
        "PF_GOOGLE_OAUTH_CLIENT_ID=cid\nPF_GOOGLE_OAUTH_CLIENT_SECRET=cs\nPF_GMAIL_REFRESH_TOKEN_GMAIL_1=rt\n"
    ))
    creds = og.RefreshableGoogleCredentials.from_env("gmail-1", profile="personal")
    og._write_cache("personal", "gmail-1", {
        "access_token": "ya29.cached", "expires_at": time.time() + 3600, "refreshed_at": time.time(),
    })
    with patch.object(og.urllib.request, "urlopen") as m:
        token = creds.get_access_token()
    assert token == "ya29.cached"
    m.assert_not_called()  # no network call


def test_get_access_token_refreshes_when_near_expiry(hermes_home: Path) -> None:
    _write_env(hermes_home, (
        "PF_GOOGLE_OAUTH_CLIENT_ID=cid\nPF_GOOGLE_OAUTH_CLIENT_SECRET=cs\nPF_GMAIL_REFRESH_TOKEN_GMAIL_1=rt\n"
    ))
    creds = og.RefreshableGoogleCredentials.from_env("gmail-1", profile="personal")
    # Cache expires inside the safety margin → must refresh
    og._write_cache("personal", "gmail-1", {
        "access_token": "ya29.stale", "expires_at": time.time() + 30, "refreshed_at": time.time(),
    })
    with patch.object(og.urllib.request, "urlopen", return_value=_fake_token_response("ya29.refreshed", 3600)):
        token = creds.get_access_token()
    assert token == "ya29.refreshed"


def test_write_access_token_to_env_replaces_existing(hermes_home: Path) -> None:
    _write_env(hermes_home, (
        "PF_GOOGLE_OAUTH_CLIENT_ID=cid\n"
        "PF_GMAIL_TOKEN_GMAIL_1=old-token\n"
        "PF_GMAIL_TOKEN_GMAIL_2=other\n"
    ))
    wrote = og.write_access_token_to_env("personal", "gmail-1", "ya29.new")
    assert wrote is True
    content = (hermes_home / "profiles" / "personal" / ".env").read_text()
    assert "PF_GMAIL_TOKEN_GMAIL_1=ya29.new" in content
    assert "PF_GMAIL_TOKEN_GMAIL_2=other" in content  # untouched


def test_write_access_token_to_env_appends_if_missing(hermes_home: Path) -> None:
    _write_env(hermes_home, "PF_GOOGLE_OAUTH_CLIENT_ID=cid\n")
    wrote = og.write_access_token_to_env("personal", "gmail-3", "ya29.added")
    assert wrote is True
    content = (hermes_home / "profiles" / "personal" / ".env").read_text()
    assert "PF_GMAIL_TOKEN_GMAIL_3=ya29.added" in content
