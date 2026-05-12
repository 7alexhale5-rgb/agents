"""Loopback-redirect OAuth provisioning for Google + Microsoft Graph.

Replaces the OAuth Playground / Azure auth-code-paste manual flow with a
local 127.0.0.1:PORT HTTP listener that captures the redirect. Operator
clicks "Allow" once in the browser; this module does everything else
(authorize-URL build, listener, code-for-token exchange, .env write,
calendar-twin alias write).

One-time prerequisite (per OAuth app):

    Google Cloud Console > Credentials > <OAuth client> > Authorized redirect URIs:
        http://127.0.0.1:8910/callback

    Azure Entra > App registrations > <app> > Authentication > Redirect URIs:
        http://localhost:8910/callback   (type: "Web"; Azure rejects 127.0.0.1)

CLI::

    python -m pf_runtime.oauth.provision google \\
        --account gmail-1 --email alex@prettyflyforai.com --profile personal \\
        --write-also gmail-1-calendar

    python -m pf_runtime.oauth.provision microsoft \\
        --account koho-m365 --email alex@kohoconsulting.com --profile personal

Each invocation:
  1. Builds the authorize URL with scopes + login_hint + access_type=offline.
  2. Starts http.server on 127.0.0.1:--port (default 8910; 8765 is commonly
     grabbed by Docker on macOS).
  3. Opens the authorize URL in the default browser via `open`.
  4. Listener captures /callback?code=... and answers with a short success page.
  5. POSTs the code to the provider token endpoint.
  6. Writes refresh_token + access_token to the profile .env. For Google,
     also writes the access_token to any --write-also alias env vars.
"""

from __future__ import annotations

import argparse
import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from pf_runtime.oauth import google as og
from pf_runtime.oauth import microsoft as om

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = og.GOOGLE_TOKEN_URL
GOOGLE_DEFAULT_SCOPES = " ".join([
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events.readonly",
    "https://www.googleapis.com/auth/calendar.freebusy",
])

MICROSOFT_DEFAULT_SCOPES = "Mail.Read Calendars.ReadBasic MailboxSettings.Read offline_access User.Read"

DEFAULT_PORT = 8910  # 8765 is commonly grabbed by Docker on macOS
DEFAULT_PATH = "/callback"

SUCCESS_HTML = b"""<!doctype html><html><head><meta charset="utf-8"><title>Connected</title>
<style>body{font:14px/1.5 -apple-system,sans-serif;padding:3rem;color:#222}h1{color:#0a6}</style>
</head><body><h1>Connected.</h1><p>You can close this tab. The pf-runtime CLI captured the
authorization code and is exchanging it for tokens now.</p></body></html>"""

FAILURE_HTML = b"""<!doctype html><html><head><meta charset="utf-8"><title>OAuth error</title>
<style>body{font:14px/1.5 -apple-system,sans-serif;padding:3rem;color:#222}h1{color:#c33}</style>
</head><body><h1>OAuth error.</h1><p>The provider returned an error or no auth code. Check
the terminal for details.</p></body></html>"""


@dataclass
class _CapturedCode:
    code: str | None = None
    error: str | None = None
    state: str | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    captured: _CapturedCode = _CapturedCode()
    expected_state: str = ""
    callback_path: str = DEFAULT_PATH

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != self.callback_path:
            self.send_response(404)
            self.send_header("Connection", "close")
            self.end_headers()
            return
        params = urllib.parse.parse_qs(parsed.query)
        code = next(iter(params.get("code", [])), None)
        error = next(iter(params.get("error", [])), None)
        state = next(iter(params.get("state", [])), None)
        # Stash captured state FIRST so the main thread sees it even if the
        # response write blocks or the connection drops mid-flight.
        _CallbackHandler.captured = _CapturedCode(code=code, error=error, state=state)
        ok = bool(code) and (not self.expected_state or state == self.expected_state)
        body = SUCCESS_HTML if ok else FAILURE_HTML
        self.send_response(200 if ok else 400)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            # Browser closed the connection before we finished writing — we
            # already captured the code, so this is fine.
            pass

    def log_message(self, fmt: str, *args: Any) -> None:
        # Quiet the default access-log line so the CLI output stays clean.
        return


def _free_port(preferred: int) -> int:
    """Return ``preferred`` if it binds; otherwise raise so the operator can pick another.

    Uses SO_REUSEADDR so a TIME_WAIT socket from a prior run on the same port
    doesn't false-positive as busy. Real conflicts (another process holding
    LISTEN) still fail.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("127.0.0.1", preferred))
    except OSError as exc:
        raise RuntimeError(
            f"port 127.0.0.1:{preferred} is busy ({exc}). "
            f"Pick another with --port and make sure it's on the OAuth client's "
            f"authorized redirect URI list."
        ) from exc
    finally:
        s.close()
    return preferred


def _open_url(url: str) -> None:
    """Open ``url`` in the OS default browser. Falls back to printing on failure."""
    if sys.platform == "darwin":
        subprocess.run(["/usr/bin/open", url], check=False)
    elif sys.platform.startswith("linux"):
        subprocess.run(["xdg-open", url], check=False)
    else:
        print(f"open this URL in your browser:\n  {url}")


def _wait_for_code(timeout_s: int = 180) -> _CapturedCode:
    """Block until the handler stashes a code (or errors), or timeout."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _CallbackHandler.captured.code or _CallbackHandler.captured.error:
            return _CallbackHandler.captured
        time.sleep(0.1)
    return _CapturedCode(error="timeout")


def _run_listener(port: int, path: str, state: str, timeout_s: int) -> _CapturedCode:
    """Start a single-shot listener, return the captured code."""
    _CallbackHandler.captured = _CapturedCode()
    _CallbackHandler.expected_state = state
    _CallbackHandler.callback_path = path
    # Allow TIME_WAIT sockets from a prior provision run to be re-bound immediately.
    http.server.HTTPServer.allow_reuse_address = True
    server = http.server.HTTPServer(("127.0.0.1", port), _CallbackHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        return _wait_for_code(timeout_s)
    finally:
        server.shutdown()
        server.server_close()


# ---------------------------------------------------------------------------
# Google provisioner
# ---------------------------------------------------------------------------


def _provision_google(args: argparse.Namespace) -> int:
    profile = args.profile
    og._load_profile_env(profile)  # populate os.environ from .env
    client_id = os.environ.get("PF_GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("PF_GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("error: PF_GOOGLE_OAUTH_CLIENT_ID and PF_GOOGLE_OAUTH_CLIENT_SECRET must be set in profile .env", file=sys.stderr)
        return 1

    port = _free_port(args.port)
    redirect_uri = f"http://127.0.0.1:{port}{args.path}"
    state = f"pf-{args.account}-{int(time.time())}"
    scope = args.scope or GOOGLE_DEFAULT_SCOPES

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    if args.email:
        params["login_hint"] = args.email
    authorize_url = f"{GOOGLE_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    print(f"[{args.account}] opening browser for {args.email or 'Google account picker'}...")
    print(f"  redirect_uri = {redirect_uri}")
    print(f"  authorize_url = {authorize_url}")
    print(f"  (if Google says redirect_uri_mismatch, add {redirect_uri} to the OAuth client at https://console.cloud.google.com/apis/credentials)")
    if not args.no_open:
        _open_url(authorize_url)
    captured = _run_listener(port, args.path, state, args.timeout)

    if captured.error or not captured.code:
        print(f"error: {captured.error or 'no code captured'}", file=sys.stderr)
        return 2

    tokens = _exchange_google_code(client_id, client_secret, captured.code, redirect_uri)
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not refresh_token or not access_token:
        print(f"error: token endpoint returned no refresh/access token: {tokens}", file=sys.stderr)
        return 3

    refresh_key = og._env_key(args.account)
    access_key = og._access_token_env_key(args.account)
    og.write_access_token_to_env(profile, args.account, access_token)  # PF_GMAIL_TOKEN_<account>
    _write_env_line(profile, refresh_key, refresh_token)
    for alias in args.write_also or []:
        og.write_access_token_to_env(profile, alias, access_token)
    also = f" (also wrote: {', '.join(args.write_also)})" if args.write_also else ""
    print(f"[{args.account}] connected: wrote {refresh_key} + {access_key}{also}")
    return 0


def _exchange_google_code(client_id: str, client_secret: str, code: str, redirect_uri: str) -> dict[str, Any]:
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_TOKEN_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Microsoft provisioner
# ---------------------------------------------------------------------------


def _provision_microsoft(args: argparse.Namespace) -> int:
    profile = args.profile
    om._load_profile_env(profile)
    client_id = os.environ.get("PF_MS_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("PF_MS_OAUTH_CLIENT_SECRET")
    tenant = os.environ.get("PF_MS_OAUTH_TENANT_ID", om.DEFAULT_TENANT)
    scopes = args.scope or os.environ.get("PF_MS_OAUTH_SCOPES", MICROSOFT_DEFAULT_SCOPES)
    if not client_id or not client_secret:
        print("error: PF_MS_OAUTH_CLIENT_ID and PF_MS_OAUTH_CLIENT_SECRET must be set in profile .env", file=sys.stderr)
        return 1

    port = _free_port(args.port)
    # Microsoft rejects bare 127.0.0.1 for Web platform redirect URIs — only
    # localhost or HTTPS are accepted. The loopback resolves the same way,
    # so the listener (which binds 127.0.0.1) still catches the callback.
    redirect_uri = f"http://localhost:{port}{args.path}"
    state = f"pf-{args.account}-{int(time.time())}"
    authorize_base = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant, safe='')}/oauth2/v2.0/authorize"

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "response_mode": "query",
        "scope": scopes,
        "state": state,
        "prompt": "consent",
    }
    if args.email:
        params["login_hint"] = args.email
    authorize_url = f"{authorize_base}?{urllib.parse.urlencode(params)}"

    print(f"[{args.account}] opening browser for {args.email or 'Microsoft account picker'}...")
    print(f"  redirect_uri = {redirect_uri}")
    print(f"  authorize_url = {authorize_url}")
    print(f"  (if Microsoft says redirect_uri_mismatch, add {redirect_uri} to the Azure app's Web redirect URIs)")
    if not args.no_open:
        _open_url(authorize_url)
    captured = _run_listener(port, args.path, state, args.timeout)

    if captured.error or not captured.code:
        print(f"error: {captured.error or 'no code captured'}", file=sys.stderr)
        return 2

    tokens = _exchange_microsoft_code(
        client_id, client_secret, captured.code, redirect_uri, scopes, tenant
    )
    refresh_token = tokens.get("refresh_token")
    access_token = tokens.get("access_token")
    if not refresh_token or not access_token:
        print(f"error: token endpoint returned no refresh/access token: {tokens}", file=sys.stderr)
        return 3

    refresh_key = om._refresh_env_key(args.account)
    access_key = om._access_token_env_key(args.account)
    om.write_env_line(profile, refresh_key, refresh_token)
    om.write_env_line(profile, access_key, access_token)
    print(f"[{args.account}] connected: wrote {refresh_key} + {access_key}")
    return 0


def _exchange_microsoft_code(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
    scope: str,
    tenant: str,
) -> dict[str, Any]:
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    token_url = f"https://login.microsoftonline.com/{urllib.parse.quote(tenant, safe='')}/oauth2/v2.0/token"
    req = urllib.request.Request(
        token_url,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
        return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]


# ---------------------------------------------------------------------------
# Shared .env writer (Google + Microsoft share format)
# ---------------------------------------------------------------------------


def _write_env_line(profile: str, key: str, value: str) -> None:
    """Replace or append ``key=value`` in the profile .env."""
    path = og._profile_env_path(profile)
    if not path.is_file():
        raise FileNotFoundError(f"profile .env not found: {path}")
    import re as _re
    content = path.read_text()
    new, n = _re.subn(rf"^{_re.escape(key)}=.*$", f"{key}={value}", content, flags=_re.M)
    if n == 0:
        if not new.endswith("\n"):
            new += "\n"
        new += f"{key}={value}\n"
    path.write_text(new)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pf_runtime.oauth.provision")
    sub = parser.add_subparsers(dest="provider", required=True)

    g = sub.add_parser("google", help="Provision a Google OAuth grant via loopback redirect")
    g.add_argument("--account", required=True, help="account_id, e.g. gmail-2")
    g.add_argument("--email", help="login_hint email so Google skips the account chooser")
    g.add_argument("--profile", default="personal")
    g.add_argument("--port", type=int, default=DEFAULT_PORT)
    g.add_argument("--path", default=DEFAULT_PATH)
    g.add_argument("--scope", help="override default scopes (space-separated)")
    g.add_argument(
        "--write-also",
        action="append",
        default=[],
        metavar="ALIAS_ID",
        help="also write PF_GMAIL_TOKEN_<UPPER(alias)> (repeatable; e.g. --write-also gmail-2-calendar)",
    )
    g.add_argument("--timeout", type=int, default=180, help="seconds to wait for callback")
    g.add_argument("--no-open", action="store_true", help="print the authorize_url but don't auto-open the browser")
    g.set_defaults(handler=_provision_google)

    m = sub.add_parser("microsoft", help="Provision a Microsoft Graph OAuth grant via loopback redirect")
    m.add_argument("--account", required=True, help="account_id, e.g. koho-m365")
    m.add_argument("--email", help="login_hint email so Microsoft skips the account chooser")
    m.add_argument("--profile", default="personal")
    m.add_argument("--port", type=int, default=DEFAULT_PORT)
    m.add_argument("--path", default=DEFAULT_PATH)
    m.add_argument("--scope", help="override default scopes (space-separated)")
    m.add_argument("--timeout", type=int, default=180, help="seconds to wait for callback")
    m.add_argument("--no-open", action="store_true", help="print the authorize_url but don't auto-open the browser")
    m.set_defaults(handler=_provision_microsoft)

    args = parser.parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
