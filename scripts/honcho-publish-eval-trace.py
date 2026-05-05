#!/usr/bin/env python3
"""
honcho-publish-eval-trace.py — publish a single eval_trace event to the agora.

Phase 1 substrate-as-bus claim: SKU eval runners write trial outcomes to Honcho
so VanClief (and any other auditor peer) can read them via the workspace search.
Publish failures must NEVER break the eval — call sites use `|| true`.

Routing (per architecture decisions):
  workspace = prettyfly-os
  session   = eval-traces-{YYYY-MM}    (rolling monthly bucket)
  peer_id   = vanclief                  (tier-4 auditor publishes the trace)

Payload schema (content as JSON string):
  { "event_type": "eval_trace", "sku": ..., "provider": ..., "date": ...,
    "passed": ..., "total": ..., "rate": ..., "wilson_lower_ci": ...,
    "manifest_hash": ..., "report_path": ... }

Usage:
  echo '{"event_type":"eval_trace","sku":"email-triage",...}' | \
    python3 scripts/honcho-publish-eval-trace.py
  # or
  python3 scripts/honcho-publish-eval-trace.py --json /path/to/trace.json

Exit codes: 0 = published, 1 = client error, 2 = server error.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib import request as urlrequest, error as urlerror

import jwt as pyjwt

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "honcho" / ".env"
HONCHO_URL = os.environ.get("HONCHO_URL", "http://localhost:8765")
WORKSPACE_ID = os.environ.get("HONCHO_WORKSPACE", "prettyfly-os")
PUBLISHER_PEER = os.environ.get("EVAL_TRACE_PUBLISHER_PEER", "vanclief")


def read_jwt_secret():
    if not ENV_FILE.is_file():
        raise SystemExit(f"FATAL: {ENV_FILE} missing")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("HONCHO_JWT_SECRET="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("FATAL: HONCHO_JWT_SECRET not set")


def mint_jwt(secret):
    return pyjwt.encode({"ad": True}, secret, algorithm="HS256")


def http_post(path, token, body):
    url = f"{HONCHO_URL}{path}"
    data = json.dumps(body).encode()
    req = urlrequest.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", type=Path, help="Path to JSON file containing the trace payload")
    args = ap.parse_args()

    if args.json:
        if not args.json.is_file():
            print(f"FAIL: {args.json} not found", file=sys.stderr)
            return 1
        payload = json.loads(args.json.read_text())
    else:
        if sys.stdin.isatty():
            print("FAIL: provide --json <path> or pipe JSON via stdin", file=sys.stderr)
            return 1
        payload = json.loads(sys.stdin.read())

    if not isinstance(payload, dict) or payload.get("event_type") != "eval_trace":
        print("FAIL: payload must be a JSON object with event_type=eval_trace", file=sys.stderr)
        return 1

    secret = read_jwt_secret()
    token = mint_jwt(secret)

    month = datetime.now(timezone.utc).strftime("%Y-%m")
    session_id = f"eval-traces-{month}"

    # Idempotent session create with publisher peer attached.
    code, _ = http_post(
        f"/v3/workspaces/{WORKSPACE_ID}/sessions",
        token,
        {"id": session_id, "peers": {PUBLISHER_PEER: {}}},
    )
    if code not in (200, 201):
        print(f"FAIL: session ensure {code}", file=sys.stderr)
        return 2

    # Add peer if session pre-existed (idempotent on Honcho's side).
    http_post(
        f"/v3/workspaces/{WORKSPACE_ID}/sessions/{session_id}/peers",
        token,
        {PUBLISHER_PEER: {}},
    )

    # Post the trace as a single message; payload is a JSON string in `content`.
    code, body = http_post(
        f"/v3/workspaces/{WORKSPACE_ID}/sessions/{session_id}/messages",
        token,
        {"messages": [{"content": json.dumps(payload), "peer_id": PUBLISHER_PEER}]},
    )
    if code not in (200, 201):
        print(f"FAIL: message post {code} {json.dumps(body)[:200]}", file=sys.stderr)
        return 2

    msg = body[0] if isinstance(body, list) and body else body
    msg_id = msg.get("id") if isinstance(msg, dict) else "?"
    print(f"published eval_trace to {WORKSPACE_ID}/{session_id} as {msg_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
