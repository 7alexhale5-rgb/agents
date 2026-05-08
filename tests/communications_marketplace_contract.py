"""Communications marketplace contract.

Keeps v1 read/propose: no send, write, delete, or calendar mutation scopes in
the SKU contract.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_DIR = ROOT / "marketplace" / "manifests" / "communications-triage"


def test_communications_manifest_is_read_and_propose() -> None:
    data = json.loads((MANIFEST_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data["autonomy"] == "read_and_propose"
    assert data["actions_v1"]["auto_apply"] == []
    assert "no_auto_send" in data["guardrails"]
    assert "no_auto_delete" in data["guardrails"]
    assert "no_auto_calendar_write" in data["guardrails"]


def test_forbidden_write_scopes_not_requested() -> None:
    text = (MANIFEST_DIR / "mcp-servers.yaml").read_text(encoding="utf-8")
    requested: list[str] = []
    in_scopes = False
    in_forbidden = False
    for raw in text.splitlines():
        line = raw.strip()
        if line == "scopes:":
            in_scopes = True
            in_forbidden = False
            continue
        if line == "forbidden_v1_scopes:":
            in_scopes = False
            in_forbidden = True
            continue
        if line.endswith(":") and not line.startswith("- "):
            in_scopes = False
            in_forbidden = False
        if in_scopes and not in_forbidden and line.startswith("- "):
            requested.append(line[2:])
    assert "Mail.Send" not in requested
    assert "Mail.ReadWrite" not in requested
    assert "Calendars.ReadWrite" not in requested
    assert "https://www.googleapis.com/auth/gmail.modify" not in requested
    assert "https://www.googleapis.com/auth/calendar.events" not in requested
