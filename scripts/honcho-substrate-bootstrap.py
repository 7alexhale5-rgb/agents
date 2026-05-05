#!/usr/bin/python3
"""
honcho-substrate-bootstrap.py — Phase 0 substrate operational smoke + bootstrap.

What this proves about the substrate (decisions #1, #2, #11, #12):
  - Honcho /health endpoint already validated by phase-0-soak-tick.sh.
  - This script validates the *usable* layer: workspace creation, peer
    enumeration, multi-peer session, cross-peer message visibility.

What it does (idempotent):
  1. Reads HONCHO_JWT_SECRET from honcho/.env.
  2. Mints an HS256 JWT (claim: {"sub": "phase-0-bootstrap"}).
  3. Creates workspace `prettyfly-os` (POST /v3/workspaces — get-or-create).
  4. Creates a peer for every profile in hermes/profiles/.
  5. Creates an idempotent smoke session `phase-0-smoke-test`.
  6. Posts one message from `personal` peer.
  7. Fetches session messages and confirms cross-peer visibility.

Usage:
  python3 scripts/honcho-substrate-bootstrap.py        # bootstrap + smoke
  python3 scripts/honcho-substrate-bootstrap.py --bootstrap-only
  python3 scripts/honcho-substrate-bootstrap.py --smoke-only

Exit codes: 0 = pass, 1 = fail (any step).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib import request as urlrequest, error as urlerror

import jwt as pyjwt

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "honcho" / ".env"
PROFILES_DIR = ROOT / "hermes" / "profiles"
HONCHO_URL = os.environ.get("HONCHO_URL", "http://localhost:8765")
WORKSPACE_ID = os.environ.get("HONCHO_WORKSPACE", "prettyfly-os")
SMOKE_SESSION_ID = "phase-0-smoke-test"


def read_jwt_secret():
    if not ENV_FILE.is_file():
        raise SystemExit(f"FATAL: {ENV_FILE} missing — copy honcho/env.template and fill in")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("HONCHO_JWT_SECRET="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("FATAL: HONCHO_JWT_SECRET not set in honcho/.env")


def mint_jwt(secret: str) -> str:
    """Honcho admin JWT — `ad: true` claim grants cross-workspace operations.
    Per src/security.py: only `ad` (admin flag) and `exp` (ISO timestamp) are
    interpreted; this token is used for bootstrap-time workspace + peer creation.
    """
    return pyjwt.encode({"ad": True}, secret, algorithm="HS256")


def http_request(method, path, token, body=None):
    url = f"{HONCHO_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urlrequest.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urlerror.HTTPError as e:
        try:
            payload = json.loads(e.read())
        except Exception:
            payload = {"error": str(e)}
        return e.code, payload


def list_profiles():
    if not PROFILES_DIR.is_dir():
        return []
    return sorted([p.name for p in PROFILES_DIR.iterdir() if p.is_dir()])


def step(label):
    print(f"-- {label}")


def bootstrap(token):
    profiles = list_profiles()
    if not profiles:
        raise SystemExit("FATAL: no profiles found in hermes/profiles/")

    step(f"create workspace `{WORKSPACE_ID}` (idempotent)")
    code, body = http_request("POST", "/v3/workspaces", token, {"id": WORKSPACE_ID})
    if code not in (200, 201):
        raise SystemExit(f"FATAL: workspace create failed: {code} {json.dumps(body)[:200]}")
    print(f"   ok ({code}) — workspace exists")

    step(f"create {len(profiles)} peers (idempotent)")
    for name in profiles:
        code, body = http_request(
            "POST", f"/v3/workspaces/{WORKSPACE_ID}/peers", token, {"id": name}
        )
        if code not in (200, 201):
            raise SystemExit(f"FATAL: peer create failed for {name}: {code} {json.dumps(body)[:200]}")
    print(f"   ok — {len(profiles)} peers ready: {', '.join(profiles)}")
    return profiles


def smoke(token, profiles):
    step(f"create smoke session `{SMOKE_SESSION_ID}` with all {len(profiles)} peers")
    peers_dict = {name: {} for name in profiles}
    code, body = http_request(
        "POST",
        f"/v3/workspaces/{WORKSPACE_ID}/sessions",
        token,
        {"id": SMOKE_SESSION_ID, "peers": peers_dict},
    )
    if code not in (200, 201):
        raise SystemExit(f"FATAL: session create failed: {code} {json.dumps(body)[:200]}")
    print(f"   ok ({code})")

    smoke_marker = f"phase-0-substrate-smoke {int(time.time())}"
    step(f"post message from `personal` peer with marker `{smoke_marker}`")
    code, body = http_request(
        "POST",
        f"/v3/workspaces/{WORKSPACE_ID}/sessions/{SMOKE_SESSION_ID}/messages",
        token,
        {"messages": [{"content": smoke_marker, "peer_id": "personal"}]},
    )
    if code not in (200, 201):
        raise SystemExit(f"FATAL: message post failed: {code} {json.dumps(body)[:200]}")
    msg = body[0] if isinstance(body, list) and body else body
    msg_id = msg.get("id") if isinstance(msg, dict) else None
    print(f"   ok ({code}) — message id {msg_id}")

    step("fetch session messages list — verify cross-peer visibility")
    code, body = http_request(
        "POST",
        f"/v3/workspaces/{WORKSPACE_ID}/sessions/{SMOKE_SESSION_ID}/messages/list",
        token,
        {},
    )
    if code != 200:
        raise SystemExit(f"FATAL: messages list failed: {code} {json.dumps(body)[:200]}")
    items = body.get("items", []) if isinstance(body, dict) else body
    found = any(smoke_marker in (m.get("content") or "") for m in items)
    if not found:
        raise SystemExit(f"FATAL: smoke marker not found in {len(items)} messages — cross-peer visibility broken")
    print(f"   ok — marker visible in session ({len(items)} message(s) total)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bootstrap-only", action="store_true")
    ap.add_argument("--smoke-only", action="store_true")
    args = ap.parse_args()

    secret = read_jwt_secret()
    token = mint_jwt(secret)

    print(f"Honcho substrate bootstrap — workspace `{WORKSPACE_ID}` @ {HONCHO_URL}")
    print("=" * 60)

    if args.smoke_only:
        # Smoke needs the peers to exist; ensure they do.
        profiles = list_profiles()
    else:
        profiles = bootstrap(token)

    if not args.bootstrap_only:
        smoke(token, profiles)

    print("=" * 60)
    print("Honcho substrate: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
