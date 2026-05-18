#!/usr/bin/env python3
"""Promptfoo exec provider for PF Runtime profile evals.

Reads the prompt from stdin and runs the local PF Runtime CLI against the
runtime profile. This script is intentionally thin so evals exercise the same
entrypoint Alex uses for manual CLI checks.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: eval_profile_prompt.py <profile>", file=sys.stderr)
        return 2
    profile = sys.argv[1]
    prompt = sys.stdin.read().strip() or os.environ.get("PROMPTFOO_PROMPT", "")
    if not prompt:
        print("missing prompt", file=sys.stderr)
        return 2

    repo = Path(__file__).resolve().parents[2]
    cmd = [
        sys.executable,
        "-m",
        "pf_runtime",
        "run",
        "--profile",
        profile,
        "--message",
        prompt,
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo / "pf-runtime")
    result = subprocess.run(  # noqa: S603
        cmd,
        cwd=repo / "pf-runtime",
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=180,
    )
    if result.returncode != 0:
        print(result.stderr.strip() or "pf_runtime eval failed", file=sys.stderr)
        return result.returncode
    print(result.stdout.removeprefix("REPLY: ").strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
