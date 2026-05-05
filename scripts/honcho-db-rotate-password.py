#!/usr/bin/python3
"""
honcho-db-rotate-password.py — sync honcho-db role password to match honcho-api .env.

When honcho-db's volume retains a stale password hash (e.g. .env was rotated after
the volume was created), honcho-api reports `password authentication failed for
user "honcho"`. Honcho's auto-migration never runs, so the schema is missing too.

This script ALTERs the honcho role password to match HONCHO_DB_PASSWORD in
~/Projects/agents/honcho/.env, leveraging the container's local-trust pg_hba.conf
(unix socket peer auth needs no password). Password is sent via psql stdin only —
never exposed on the command line or in environment variables.

Idempotent. Safe to run any time the api is showing auth failures.

After running this, restart honcho-api so migrations + workspace creation succeed.
"""
import os
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "honcho" / ".env"


def read_env_password():
    if not ENV_FILE.is_file():
        raise SystemExit(f"FATAL: {ENV_FILE} missing")
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("HONCHO_DB_PASSWORD="):
            v = line.split("=", 1)[1].strip().strip('"').strip("'")
            return v
    raise SystemExit("FATAL: HONCHO_DB_PASSWORD not set in honcho/.env")


def rotate(password: str) -> None:
    # Use SQL parameter-style quoting via dollar-quoted string to avoid escaping
    # special characters in the password. Honcho's password is a 64-hex-char
    # string per runbook, so this is belt-and-suspenders.
    safe_tag = "honchopw"
    while f"${safe_tag}$" in password:
        safe_tag += "x"
    sql = f"ALTER ROLE honcho WITH PASSWORD ${safe_tag}${password}${safe_tag}$;\n"

    # Connect via Unix socket inside the container — pg_hba.conf has local trust,
    # so no auth required for peer-auth.
    cmd = [
        "docker", "exec", "-i", "honcho-db",
        "psql", "-h", "/var/run/postgresql", "-U", "honcho", "-d", "honcho", "-v", "ON_ERROR_STOP=1",
    ]

    proc = subprocess.run(
        cmd,
        input=sql,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        sys.stderr.write(f"FAIL stderr: {proc.stderr.strip()}\n")
        raise SystemExit(proc.returncode)
    print(proc.stdout.strip() or "ALTER ROLE")


def main():
    pwd = read_env_password()
    rotate(pwd)
    print("honcho role password rotated to match .env")
    print("Next: restart honcho-api  →  (cd honcho && docker compose up -d --force-recreate honcho-api)")


if __name__ == "__main__":
    main()
