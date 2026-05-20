"""Tests for pf_runtime.oauth.microsoft — no network calls.

Mocks urllib.request.urlopen so we never hit login.microsoftonline.com.
"""

from __future__ import annotations

import io
import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pf_runtime.oauth import microsoft as om


@pytest.fixture
def hermes_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "hermes"
    profile = home / "profiles" / "personal"
    profile.mkdir(parents=True)
    monkeypatch.setenv("HERMES_HOME", str(home))
    for k in (
        "PF_MS_OAUTH_CLIENT_ID",
        "PF_MS_OAUTH_CLIENT_SECRET",
        "PF_MS_OAUTH_TENANT_ID",
        "PF_MS_OAUTH_SCOPES",
        "PF_GRAPH_REFRESH_TOKEN_KOHO_M365",
        "PF_GRAPH_TOKEN_KOHO_M365",
    ):
        monkeypatch.delenv(k, raising=False)
    return home


def _write_env(home: Path, contents: str) -> None:
    (home / "profiles" / "personal" / ".env").write_text(contents)


def _fake_token_response(
    access_token: str = "eyJ.new",
    expires_in: int = 3600,
    refresh_token: str | None = "rt-new",
) -> io.BytesIO:
    body_dict: dict[str, object] = {
        "access_token": access_token,
        "expires_in": expires_in,
        "token_type": "Bearer",
        "scope": "Mail.Read offline_access",
    }
    if refresh_token is not None:
        body_dict["refresh_token"] = refresh_token
    body = json.dumps(body_dict).encode()
    resp = io.BytesIO(body)
    resp.__enter__ = lambda *a: resp  # type: ignore[method-assign]
    resp.__exit__ = lambda *a: None  # type: ignore[method-assign]
    return resp


def test_env_key_uppercase_underscore() -> None:
    assert om._refresh_env_key("koho-m365") == "PF_GRAPH_REFRESH_TOKEN_KOHO_M365"
    assert om._access_token_env_key("koho-m365") == "PF_GRAPH_TOKEN_KOHO_M365"


def test_token_endpoint_uses_common_by_default() -> None:
    assert om._token_endpoint("common") == "https://login.microsoftonline.com/common/oauth2/v2.0/token"


def test_token_endpoint_uses_specific_tenant() -> None:
    url = om._token_endpoint("00000000-1111-2222-3333-444444444444")
    assert "/00000000-1111-2222-3333-444444444444/" in url


def test_from_env_missing_vars_raises(hermes_home: Path) -> None:
    _write_env(hermes_home, "")
    with pytest.raises(ValueError, match="missing env vars"):
        om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")


def test_from_env_loads_from_profile_env(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=app-cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=app-secret\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt-initial\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    assert creds.client_id == "app-cid"
    assert creds.client_secret == "app-secret"
    assert creds.refresh_token == "rt-initial"
    assert creds.tenant == "common"
    assert "Mail.Read" in creds.scopes


def test_from_env_respects_tenant_and_scope_overrides(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=app-cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=app-secret\n"
            "PF_MS_OAUTH_TENANT_ID=koho-tenant-guid\n"
            "PF_MS_OAUTH_SCOPES=Mail.Read offline_access\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt-initial\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    assert creds.tenant == "koho-tenant-guid"
    assert creds.scopes == "Mail.Read offline_access"


def test_refresh_writes_cache_and_returns_token(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=cs\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt-old\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    with patch.object(om.urllib.request, "urlopen", return_value=_fake_token_response("eyJ.fresh", 3600, "rt-rotated")):
        record = creds.refresh()
    assert record["access_token"] == "eyJ.fresh"
    cache = om._read_cache("personal", "koho-m365")
    assert cache is not None
    assert cache["access_token"] == "eyJ.fresh"
    assert cache["expires_at"] > time.time()


def test_refresh_captures_rotated_refresh_token(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=cs\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt-old\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    with patch.object(om.urllib.request, "urlopen", return_value=_fake_token_response(refresh_token="rt-rotated")):
        creds.refresh()
    assert creds.refresh_token == "rt-rotated"


def test_refresh_keeps_token_when_microsoft_omits_rotation(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=cs\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt-old\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    with patch.object(om.urllib.request, "urlopen", return_value=_fake_token_response(refresh_token=None)):
        creds.refresh()
    assert creds.refresh_token == "rt-old"


def test_get_access_token_uses_cache_when_fresh(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=cs\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    om._write_cache(
        "personal",
        "koho-m365",
        {"access_token": "eyJ.cached", "expires_at": time.time() + 3600, "refreshed_at": time.time()},
    )
    with patch.object(om.urllib.request, "urlopen") as m:
        token = creds.get_access_token()
    assert token == "eyJ.cached"
    m.assert_not_called()


def test_get_access_token_refreshes_when_near_expiry(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=cid\n"
            "PF_MS_OAUTH_CLIENT_SECRET=cs\n"
            "PF_GRAPH_REFRESH_TOKEN_KOHO_M365=rt\n"
        ),
    )
    creds = om.RefreshableMicrosoftCredentials.from_env("koho-m365", profile="personal")
    om._write_cache(
        "personal",
        "koho-m365",
        {"access_token": "eyJ.stale", "expires_at": time.time() + 30, "refreshed_at": time.time()},
    )
    with patch.object(om.urllib.request, "urlopen", return_value=_fake_token_response("eyJ.fresh")):
        token = creds.get_access_token()
    assert token == "eyJ.fresh"


def test_write_env_line_replaces_existing(hermes_home: Path) -> None:
    _write_env(
        hermes_home,
        (
            "PF_MS_OAUTH_CLIENT_ID=cid\n"
            "PF_GRAPH_TOKEN_KOHO_M365=old-token\n"
            "PF_GRAPH_TOKEN_OTHER=other\n"
        ),
    )
    wrote = om.write_env_line("personal", "PF_GRAPH_TOKEN_KOHO_M365", "eyJ.new")
    assert wrote is True
    content = (hermes_home / "profiles" / "personal" / ".env").read_text()
    assert "PF_GRAPH_TOKEN_KOHO_M365=eyJ.new" in content
    assert "PF_GRAPH_TOKEN_OTHER=other" in content


def test_write_env_line_appends_when_missing(hermes_home: Path) -> None:
    _write_env(hermes_home, "PF_MS_OAUTH_CLIENT_ID=cid\n")
    wrote = om.write_env_line("personal", "PF_GRAPH_TOKEN_KOHO_M365", "eyJ.added")
    assert wrote is True
    content = (hermes_home / "profiles" / "personal" / ".env").read_text()
    assert "PF_GRAPH_TOKEN_KOHO_M365=eyJ.added" in content
