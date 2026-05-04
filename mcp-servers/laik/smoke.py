#!/usr/bin/env python3
"""
Smoke test for the LAIK MCP server.

Sends list-tools + status calls over stdio. Doesn't actually run a query against
ConsultOps PG (that would require the tenant DB to be reachable from the laptop);
just verifies the wrapper boots and the LAIK_ROOT import path resolves.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SERVER = HERE / "server.py"


def main() -> int:
    env = os.environ.copy()
    env.setdefault("LAIK_ROOT", str(Path.home() / "Projects" / "local-ai-kit"))

    proc = subprocess.Popen(
        ["python3", str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
    )

    def send(req: dict) -> None:
        print("→", json.dumps(req))
        assert proc.stdin is not None
        proc.stdin.write(json.dumps(req) + "\n")
        proc.stdin.flush()

    def recv_line() -> str | None:
        assert proc.stdout is not None
        return proc.stdout.readline()

    # initialize
    send({
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "smoke", "version": "0"},
        },
    })
    line = recv_line()
    print("←", (line or "").strip()[:300])

    # list tools
    send({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    line = recv_line()
    if line:
        try:
            msg = json.loads(line)
            tools = msg.get("result", {}).get("tools", [])
            print(f"← tools/list returned {len(tools)} tools: {[t['name'] for t in tools]}")
        except json.JSONDecodeError:
            print("← (raw)", line.strip()[:300])

    # status call
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "laik_status", "arguments": {}}})
    line = recv_line()
    if line:
        print("←", (line or "").strip()[:600])

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

    err = proc.stderr.read() if proc.stderr else ""
    if err.strip():
        print("---stderr---")
        print(err[:1000])

    return 0


if __name__ == "__main__":
    sys.exit(main())
