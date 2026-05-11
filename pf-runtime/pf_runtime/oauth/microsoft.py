"""Refreshable Microsoft Graph OAuth credentials for pf-runtime connectors.

Same shape as ``pf_runtime.oauth.google``, with two Microsoft-specific tweaks:

1. Microsoft rotates the refresh_token on every exchange when ``offline_access``
   is in scope — we always write the new one back to ``.env`` so the next
   refresh succeeds.
2. Tenant is configurable via ``PF_MS_OAUTH_TENANT_ID`` (defaults to
   ``common`` for multitenant Azure AD apps).

Env contract (per profile .env)::

    PF_MS_OAUTH_CLIENT_ID=<Azure app registration "Application (client) ID">
    PF_MS_OAUTH_CLIENT_SECRET=<app secret value, NOT secret id>
    PF_MS_OAUTH_TENANT_ID=common                                  # optional
    PF_MS_OAUTH_SCOPES="Mail.Read Calendars.ReadBasic MailboxSettings.Read offline_access"  # optional
    PF_GRAPH_REFRESH_TOKEN_<ACCOUNT_ID_UPPER>=<per-account refresh token>

Operator usage::

    python -m pf_runtime.oauth.microsoft refresh --account koho-m365 --profile personal

That command refreshes the access token, writes it back to .env's
``PF_GRAPH_TOKEN_<account>`` line, also writes back the rotated
``PF_GRAPH_REFRESH_TOKEN_<account>`` line, and exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXPIRY_SAFETY_MARGIN_S = 60
DEFAULT_TENANT = "common"
DEFAULT_SCOPES = "Mail.Read Calendars.ReadBasic MailboxSettings.Read offline_access"


def _token_endpoint(tenant: str) -> str:
    return f"https://login.microsoftonline.com/{urllib.parse.quote(tenant, safe='')}/oauth2/v2.0/token"


def _refresh_env_key(account_id: str) -> str:
    """Refresh-token env var name for an account_id (e.g. 'koho-m365' -> 'PF_GRAPH_REFRESH_TOKEN_KOHO_M365')."""
    return "PF_GRAPH_REFRESH_TOKEN_" + account_id.upper().replace("-", "_")


def _access_token_env_key(account_id: str) -> str:
    """Access-token env var name (matches GraphClient's read path via account_registry)."""
    return "PF_GRAPH_TOKEN_" + account_id.upper().replace("-", "_")


def _profile_env_path(profile: str) -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "profiles" / profile / ".env"


def _cache_path(profile: str, account_id: str) -> Path:
    return _profile_env_path(profile).parent / "oauth-cache" / f"{account_id}.json"


@dataclass
class RefreshableMicrosoftCredentials:
    account_id: str
    profile: str
    client_id: str
    client_secret: str
    refresh_token: str
    tenant: str = DEFAULT_TENANT
    scopes: str = DEFAULT_SCOPES

    @classmethod
    def from_env(cls, account_id: str, *, profile: str = "personal") -> "RefreshableMicrosoftCredentials":
        _load_profile_env(profile)
        cid = os.environ.get("PF_MS_OAUTH_CLIENT_ID")
        cs = os.environ.get("PF_MS_OAUTH_CLIENT_SECRET")
        rt = os.environ.get(_refresh_env_key(account_id))
        tenant = os.environ.get("PF_MS_OAUTH_TENANT_ID", DEFAULT_TENANT)
        scopes = os.environ.get("PF_MS_OAUTH_SCOPES", DEFAULT_SCOPES)
        missing = [
            n for n, v in [
                ("PF_MS_OAUTH_CLIENT_ID", cid),
                ("PF_MS_OAUTH_CLIENT_SECRET", cs),
                (_refresh_env_key(account_id), rt),
            ] if not v
        ]
        if missing:
            raise ValueError(f"missing env vars: {', '.join(missing)}")
        return cls(
            account_id=account_id,
            profile=profile,
            client_id=cid,  # type: ignore[arg-type]
            client_secret=cs,  # type: ignore[arg-type]
            refresh_token=rt,  # type: ignore[arg-type]
            tenant=tenant,
            scopes=scopes,
        )

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if expired (or near-expiry)."""
        cached = _read_cache(self.profile, self.account_id)
        if cached and cached["expires_at"] > time.time() + EXPIRY_SAFETY_MARGIN_S:
            return cached["access_token"]
        return self.refresh()["access_token"]

    def refresh(self) -> dict[str, Any]:
        """Mint a fresh access token via Microsoft's token endpoint, cache it, return the cache record.

        Microsoft rotates the refresh_token on every exchange when offline_access is in scope.
        The rotated refresh_token is captured on ``self`` AND persisted to the cache file so
        a process crash between refresh() and the .env write-back doesn't strand the operator
        with a dead refresh token.
        """
        body = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "scope": self.scopes,
        }).encode("utf-8")
        req = urllib.request.Request(
            _token_endpoint(self.tenant),
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310 - fixed host
            payload = json.loads(resp.read().decode("utf-8"))
        if "access_token" not in payload:
            raise RuntimeError(f"refresh failed: no access_token in response: {payload}")
        new_refresh = payload.get("refresh_token")
        rotated = bool(new_refresh) and new_refresh != self.refresh_token
        if rotated:
            self.refresh_token = new_refresh
        record = {
            "access_token": payload["access_token"],
            "expires_at": time.time() + int(payload.get("expires_in", 3600)),
            "refreshed_at": time.time(),
            "rotated_refresh_token": rotated,
            # Persist the live refresh_token so the .env can be repaired if the
            # CLI dies before it writes back.
            "refresh_token": self.refresh_token,
        }
        _write_cache(self.profile, self.account_id, record)
        return record


def _load_profile_env(profile: str) -> None:
    path = _profile_env_path(profile)
    if not path.is_file():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _read_cache(profile: str, account_id: str) -> dict[str, Any] | None:
    path = _cache_path(profile, account_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text())  # type: ignore[no-any-return]
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(profile: str, account_id: str, record: dict[str, Any]) -> None:
    path = _cache_path(profile, account_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2))
    path.chmod(0o600)


def write_env_line(profile: str, key: str, value: str) -> bool:
    """Replace ``key=`` in profile .env (or append). Returns True if a line was written."""
    path = _profile_env_path(profile)
    if not path.is_file():
        raise FileNotFoundError(f"profile .env not found: {path}")
    content = path.read_text()
    new, n = re.subn(rf"^{re.escape(key)}=.*$", f"{key}={value}", content, flags=re.M)
    if n == 0:
        if not new.endswith("\n"):
            new += "\n"
        new += f"{key}={value}\n"
        n = 1
    path.write_text(new)
    return n > 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    try:
        creds = RefreshableMicrosoftCredentials.from_env(args.account, profile=args.profile)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    prior_refresh = creds.refresh_token
    record = creds.refresh()
    if args.write_env:
        write_env_line(args.profile, _access_token_env_key(args.account), record["access_token"])
        rotated = creds.refresh_token != prior_refresh
        if rotated:
            write_env_line(args.profile, _refresh_env_key(args.account), creds.refresh_token)
        rotation_note = " (refresh_token rotated)" if rotated else ""
        print(
            f"refreshed {args.account}: token updated in profile .env, "
            f"expires in {int(record['expires_at'] - time.time())}s{rotation_note}"
        )
    else:
        print(
            f"refreshed {args.account}: expires in {int(record['expires_at'] - time.time())}s "
            "(cache only)"
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pf_runtime.oauth.microsoft")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_refresh = sub.add_parser("refresh", help="refresh access token for an account")
    p_refresh.add_argument("--account", required=True, help="account_id, e.g. koho-m365")
    p_refresh.add_argument("--profile", default="personal")
    p_refresh.add_argument(
        "--no-write-env",
        dest="write_env",
        action="store_false",
        help="don't update PF_GRAPH_TOKEN_<account> / PF_GRAPH_REFRESH_TOKEN_<account> in .env",
    )
    p_refresh.set_defaults(write_env=True)
    args = parser.parse_args(argv)
    if args.cmd == "refresh":
        return _cmd_refresh(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
