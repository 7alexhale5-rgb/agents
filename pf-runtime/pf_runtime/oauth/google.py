"""Refreshable Google OAuth credentials for pf-runtime connectors.

Replaces the manual OAuth Playground -> .env paste loop with an automatic
refresh-token exchange. Cherry-picked from onyx-dot-app/onyx's
`google_auth.get_google_oauth_creds` pattern, simplified to:

- stdlib urllib only (no google-auth dep; matches model_adapter.py style)
- per-account refresh tokens in profile .env
- shared client_id/client_secret across accounts (same OAuth app)
- file cache at ~/.hermes/profiles/<profile>/oauth-cache/<account_id>.json

Env contract (per profile .env):
    PF_GOOGLE_OAUTH_CLIENT_ID=<app client id, shared across accounts>
    PF_GOOGLE_OAUTH_CLIENT_SECRET=<app client secret, shared>
    PF_GMAIL_REFRESH_TOKEN_<ACCOUNT_ID_UPPER>=<per-account refresh token>

Usage from CLI (typical operator path):
    python -m pf_runtime.oauth.google refresh --account gmail-1 --profile personal

That command refreshes the access token, writes it back to .env's
PF_GMAIL_TOKEN_<account> line, and exits 0. Existing Codex clients keep
reading PF_GMAIL_TOKEN_* unchanged; this just rotates the value for them.

Usage from code (post-Codex-merge integration; not wired yet):
    creds = RefreshableGoogleCredentials.from_env("gmail-1", profile="personal")
    headers = {"Authorization": f"Bearer {creds.get_access_token()}"}
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

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
EXPIRY_SAFETY_MARGIN_S = 60


def _env_key(account_id: str) -> str:
    """Refresh-token env var name for an account_id (e.g. 'gmail-1' -> 'PF_GMAIL_REFRESH_TOKEN_GMAIL_1')."""
    return "PF_GMAIL_REFRESH_TOKEN_" + account_id.upper().replace("-", "_")


def _access_token_env_key(account_id: str) -> str:
    """Access-token env var name (matches Codex's clients' read path)."""
    return "PF_GMAIL_TOKEN_" + account_id.upper().replace("-", "_")


def _profile_env_path(profile: str) -> Path:
    return Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "profiles" / profile / ".env"


def _cache_path(profile: str, account_id: str) -> Path:
    return _profile_env_path(profile).parent / "oauth-cache" / f"{account_id}.json"


@dataclass
class RefreshableGoogleCredentials:
    account_id: str
    profile: str
    client_id: str
    client_secret: str
    refresh_token: str

    @classmethod
    def from_env(cls, account_id: str, *, profile: str = "personal") -> RefreshableGoogleCredentials:
        # Load profile .env into os.environ if not already set
        _load_profile_env(profile)
        cid = os.environ.get("PF_GOOGLE_OAUTH_CLIENT_ID")
        cs = os.environ.get("PF_GOOGLE_OAUTH_CLIENT_SECRET")
        rt = os.environ.get(_env_key(account_id))
        missing = [n for n, v in [("PF_GOOGLE_OAUTH_CLIENT_ID", cid),
                                   ("PF_GOOGLE_OAUTH_CLIENT_SECRET", cs),
                                   (_env_key(account_id), rt)] if not v]
        if missing:
            raise ValueError(f"missing env vars: {', '.join(missing)}")
        return cls(account_id=account_id, profile=profile, client_id=cid, client_secret=cs, refresh_token=rt)  # type: ignore[arg-type]

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if expired (or near-expiry)."""
        cached = _read_cache(self.profile, self.account_id)
        if cached and cached["expires_at"] > time.time() + EXPIRY_SAFETY_MARGIN_S:
            return str(cached["access_token"])
        return str(self.refresh()["access_token"])

    def refresh(self) -> dict[str, Any]:
        """Mint a fresh access token via Google's token endpoint, cache it, return the cache record."""
        body = urllib.parse.urlencode({
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        req = urllib.request.Request(
            GOOGLE_TOKEN_URL,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:  # nosec B310 - fixed host
            payload = json.loads(resp.read().decode("utf-8"))
        if "access_token" not in payload:
            raise RuntimeError(f"refresh failed: no access_token in response: {payload}")
        record = {
            "access_token": payload["access_token"],
            "expires_at": time.time() + int(payload.get("expires_in", 3600)),
            "refreshed_at": time.time(),
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


def write_access_token_to_env(profile: str, account_id: str, access_token: str) -> bool:
    """Replace the PF_GMAIL_TOKEN_<ACCOUNT> line in profile .env. Returns True if a line was updated."""
    path = _profile_env_path(profile)
    if not path.is_file():
        raise FileNotFoundError(f"profile .env not found: {path}")
    key = _access_token_env_key(account_id)
    content = path.read_text()
    new, n = re.subn(rf"^{re.escape(key)}=.*$", f"{key}={access_token}", content, flags=re.M)
    if n == 0:
        # Append if missing
        if not new.endswith("\n"):
            new += "\n"
        new += f"{key}={access_token}\n"
        n = 1
    path.write_text(new)
    return n > 0


def _cmd_refresh(args: argparse.Namespace) -> int:
    try:
        creds = RefreshableGoogleCredentials.from_env(args.account, profile=args.profile)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    record = creds.refresh()
    if args.write_env:
        wrote = write_access_token_to_env(args.profile, args.account, record["access_token"])
        msg = "updated" if wrote else "appended"
        also_msg = ""
        if args.write_also:
            for alias in args.write_also:
                write_access_token_to_env(args.profile, alias, record["access_token"])
            also_msg = f" (also wrote: {', '.join(args.write_also)})"
        print(
            f"refreshed {args.account}: token {msg} in profile .env, "
            f"expires in {int(record['expires_at'] - time.time())}s{also_msg}"
        )
    else:
        print(f"refreshed {args.account}: expires in {int(record['expires_at'] - time.time())}s (cache only)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pf_runtime.oauth.google")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_refresh = sub.add_parser("refresh", help="refresh access token for an account")
    p_refresh.add_argument("--account", required=True, help="account_id, e.g. gmail-1")
    p_refresh.add_argument("--profile", default="personal")
    p_refresh.add_argument(
        "--write-also",
        action="append",
        default=[],
        metavar="ALIAS_ID",
        help=(
            "Also write the access token to PF_GMAIL_TOKEN_<UPPER(alias)>. "
            "Repeatable. Use when one OAuth grant covers multiple registry "
            "accounts (e.g. --write-also gmail-1-calendar)."
        ),
    )
    p_refresh.add_argument("--no-write-env", dest="write_env", action="store_false",
                           help="don't update PF_GMAIL_TOKEN_<account> in .env")
    p_refresh.set_defaults(write_env=True)
    args = parser.parse_args(argv)
    if args.cmd == "refresh":
        return _cmd_refresh(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
