from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import ClassVar

import pytest

from pf_runtime.config import Profile
from pf_runtime.runtime import builtin_tools as builtin_tools_module
from pf_runtime.runtime.builtin_tools import (
    AtlasRecordFollowUpTool,
    FleetSnapshotTool,
    builtin_tools_for_profile,
    packet_to_json,
)
from pf_runtime.runtime.tool_dispatch import ToolContext


def test_builtin_tools_loaded_from_profile_config(tmp_path: Path) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    (profile.env_path.parent / "config.yaml").write_text(
        "tools:\n  builtin:\n    - fleet.snapshot\n    - business.scorecard.snapshot\n    - atlas.propose_action\n",
        encoding="utf-8",
    )

    tools = builtin_tools_for_profile(profile)

    assert [tool.name for tool in tools] == [
        "fleet.snapshot",
        "business.scorecard.snapshot",
        "atlas.propose_action",
    ]


def test_builtin_tools_loads_atlas_follow_up_tool(tmp_path: Path) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    (profile.env_path.parent / "config.yaml").write_text(
        "tools:\n  builtin:\n    - atlas.record_follow_up\n",
        encoding="utf-8",
    )

    tools = builtin_tools_for_profile(profile)

    assert [tool.name for tool in tools] == ["atlas.record_follow_up"]


@pytest.mark.asyncio
async def test_fleet_snapshot_returns_aggregates_without_raw_messages(tmp_path: Path) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    _write_buffer(hermes_home / "profiles" / "atlas-ceo" / "pf_buffer.sqlite")
    agents_repo = _make_agents_repo(tmp_path)
    usage_db = _make_usage_db(tmp_path)

    profile = _profile(hermes_home, "atlas-ceo")
    tool = FleetSnapshotTool(profile=profile, agents_repo=agents_repo, api_usage_db=usage_db)

    result = await tool.invoke({}, ToolContext(profile_slug="atlas-ceo", session_id="s"))
    payload = packet_to_json(result.output)

    assert result.ok is True
    assert result.output["packet_type"] == "atlas.source_packet.v2"
    assert result.output["authority"] == "read_only"
    assert result.output["source_mode"] == "local_fallback"
    assert "private Slack sentence" not in payload
    assert "atlas-ceo" in payload
    assert "recent_daily_summaries" in payload
    json.dumps(result.output)


@pytest.mark.asyncio
async def test_get_json_rejects_html_login_page(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeResponse:
        headers: ClassVar[dict[str, str]] = {"Content-Type": "text/html; charset=utf-8"}

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"<html><body>login</body></html>"

    def fake_urlopen(request: object, timeout: int) -> FakeResponse:
        del request, timeout
        return FakeResponse()

    monkeypatch.setattr(builtin_tools_module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="auth_redirect_html"):
        await builtin_tools_module._get_json("http://pfos.local/api/source", token="tok")


@pytest.mark.asyncio
async def test_atlas_propose_action_requires_source_summary(tmp_path: Path) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    tool = next(
        tool
        for tool in builtin_tools_for_profile_with_names(
            profile,
            ["atlas.propose_action"],
        )
        if tool.name == "atlas.propose_action"
    )

    result = await tool.invoke(
        {
            "recommended_action": "Narrow Atlas to CEO briefs.",
            "door_type": "two-way",
            "approval_gate": "Alex approval.",
            "expected_upside": "Better weekly decisions.",
            "downside_risk": "Less feature breadth.",
            "stop_doing": "Adding speculative tools.",
            "confidence": 0.8,
        },
        ToolContext(profile_slug="atlas-ceo", session_id="s"),
    )

    assert result.ok is False
    assert result.error == "source_packet_ref_or_evidence_required"


@pytest.mark.asyncio
async def test_atlas_propose_action_requires_verified_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    (profile.env_path).write_text(
        "PFOS_BASE_URL=http://pfos.local\nPFOS_ATLAS_ACTION_TOKEN=tok\n",
        encoding="utf-8",
    )
    tool = next(
        tool
        for tool in builtin_tools_for_profile_with_names(
            profile,
            ["atlas.propose_action"],
        )
        if tool.name == "atlas.propose_action"
    )

    async def fake_post_json(url: str, *, token: str, payload: dict):
        del url, token, payload
        return {"ok": True, "action_id": "a1", "event_id": "e1"}

    monkeypatch.setattr(builtin_tools_module, "_post_json", fake_post_json)

    result = await tool.invoke(
        _proposal_args(),
        ToolContext(profile_slug="atlas-ceo", session_id="s"),
    )

    assert result.ok is False
    assert result.error == "receipt_unverified"


@pytest.mark.asyncio
async def test_atlas_propose_action_returns_verified_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    (profile.env_path).write_text(
        "PFOS_BASE_URL=http://pfos.local\nPFOS_ATLAS_ACTION_TOKEN=tok\n",
        encoding="utf-8",
    )
    tool = next(
        tool
        for tool in builtin_tools_for_profile_with_names(
            profile,
            ["atlas.propose_action"],
        )
        if tool.name == "atlas.propose_action"
    )

    posted: list[dict] = []

    async def fake_post_json(url: str, *, token: str, payload: dict):
        del url, token, payload
        return {
            "ok": True,
            "action_id": "a1",
            "event_id": "e1",
            "receipt": {
                "verified": True,
                "action_id": "a1",
                "event_id": "e1",
                "status": "proposed",
                "executed": False,
                "action_name": "atlas.decision_proposal",
            },
        }

    async def capturing_post_json(url: str, *, token: str, payload: dict):
        posted.append(payload)
        return await fake_post_json(url, token=token, payload=payload)

    monkeypatch.setattr(builtin_tools_module, "_post_json", capturing_post_json)

    result = await tool.invoke(
        _proposal_args(),
        ToolContext(profile_slug="atlas-ceo", session_id="s"),
    )

    assert result.ok is True
    assert result.output["status"] == "proposed_only"
    assert result.output["verified"] is True
    assert result.output["action_id"] == "a1"
    assert result.output["event_id"] == "e1"
    assert result.output["silo_slug"] == "prettyfly"
    assert result.output["executed"] is False
    assert result.output["slack_card"] == {
        "action_id": "a1",
        "silo_slug": "prettyfly",
        "title": "Approve Atlas weekly operating focus",
        "summary": "Atlas found too many competing priorities.",
        "priority": "high",
        "risk_level": "medium",
        "pfos_href": "/agents/atlas-ceo",
    }
    params = posted[0]["params_json"]
    assert params["schema_version"] == "atlas.decision_proposal.v1"
    assert params["title"] == "Approve Atlas weekly operating focus"
    assert params["private_payload_redacted"] is True
    assert params["model_route"] == "anthropic:claude-sonnet-4-6"
    assert params["model_route_status"] == "premium"
    assert params["model_route_degraded"] is False
    assert posted[0]["trace_id"].startswith("atlas-run-")
    assert posted[0]["service"] == "atlas"
    assert posted[0]["skill_slug"] == "approval-proposal-draft"
    assert params["evidence"] == [
        {
            "label": "Recent Atlas planning run",
            "source_type": "run",
            "href": "/observability",
            "confidence": 0.9,
        }
    ]


@pytest.mark.asyncio
async def test_atlas_propose_action_defaults_missing_evidence_href_to_internal_route(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    profile.env_path.write_text(
        "PFOS_BASE_URL=https://os.prettyflyforai.com\nPFOS_ATLAS_ACTION_TOKEN=t\n",
        encoding="utf-8",
    )
    tool = builtin_tools_module.AtlasProposeActionTool(profile=profile)
    posted: list[dict] = []

    async def fake_post_json(url: str, *, token: str, payload: dict):
        del url, token
        posted.append(payload)
        return {
            "ok": True,
            "receipt": {
                "verified": True,
                "action_id": "a1",
                "event_id": "e1",
                "status": "proposed",
                "executed": False,
                "action_name": "atlas.decision_proposal",
            },
        }

    monkeypatch.setattr(builtin_tools_module, "_post_json", fake_post_json)
    args = _proposal_args()
    args["evidence"] = [{"label": "Recent Atlas event", "source_type": "event"}]

    result = await tool.invoke(args, ToolContext(profile_slug="atlas-ceo", session_id="s"))

    assert result.ok is True
    assert posted[0]["params_json"]["evidence"] == [
        {
            "label": "Recent Atlas event",
            "source_type": "event",
            "href": "/observability",
        }
    ]


@pytest.mark.asyncio
async def test_atlas_record_follow_up_requires_pfos_event_config(tmp_path: Path) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    tool = AtlasRecordFollowUpTool(profile=profile)

    result = await tool.invoke(
        _follow_up_args(),
        ToolContext(profile_slug="atlas-ceo", session_id="s"),
    )

    assert result.ok is False
    assert result.error == "pfos_agent_event_not_configured"


@pytest.mark.asyncio
async def test_atlas_record_follow_up_requires_source_ids(tmp_path: Path) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    profile.env_path.write_text(
        "PFOS_AGENT_EVENT_URL=https://os.prettyflyforai.com/api/silos/prettyfly/agent-event\n"
        "PFOS_AGENT_EVENT_TOKEN=tok\n",
        encoding="utf-8",
    )
    tool = AtlasRecordFollowUpTool(profile=profile)
    args = _follow_up_args()
    args["source_action_id"] = ""

    result = await tool.invoke(args, ToolContext(profile_slug="atlas-ceo", session_id="s"))

    assert result.ok is False
    assert result.error == "source_ids_required"


@pytest.mark.asyncio
async def test_atlas_record_follow_up_writes_safe_ready_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    hermes_home = _make_runtime_profile(tmp_path, "atlas-ceo")
    profile = _profile(hermes_home, "atlas-ceo")
    profile.env_path.write_text(
        "PFOS_AGENT_EVENT_URL=https://os.prettyflyforai.com/api/silos/prettyfly/agent-event\n"
        "PFOS_AGENT_EVENT_TOKEN=tok\n",
        encoding="utf-8",
    )
    tool = AtlasRecordFollowUpTool(profile=profile)
    posted: list[dict] = []

    async def fake_post_json(url: str, *, token: str, payload: dict):
        assert url.endswith("/api/silos/prettyfly/agent-event")
        assert token == "tok"
        posted.append(payload)
        return {"ok": True, "event_id": "ready-event-1"}

    monkeypatch.setattr(builtin_tools_module, "_post_json", fake_post_json)

    result = await tool.invoke(
        _follow_up_args(),
        ToolContext(profile_slug="atlas-ceo", session_id="session-1"),
    )

    assert result.ok is True
    assert result.output == {
        "verified": True,
        "event_id": "ready-event-1",
        "status": "completed",
        "source_follow_up_event_id": "queued-event-1",
        "source_action_id": "action-1",
        "executed": False,
    }
    assert posted[0]["type"] == "atlas.follow_up.ready"
    assert posted[0]["status"] == "completed"
    assert posted[0]["agent_slug"] == "atlas-ceo"
    assert posted[0]["surface"] == "pf_runtime"
    assert posted[0]["skill_slug"] == "weekly-ceo-operating-loop"
    assert posted[0]["data"] == {
        "kind": "atlas_decision_follow_up",
        "source_follow_up_event_id": "queued-event-1",
        "source_action_id": "action-1",
        "approved_decision_title": "Approve Atlas weekly operating focus",
        "next_action": "Alex confirms the operating focus.",
        "watch_item": "Watch whether pending decisions shrink.",
        "non_action": "Do not dispatch or execute work.",
        "review_timing": "Review in 24h.",
        "private_payload_redacted": True,
        "execution_triggered": False,
    }


def _make_runtime_profile(tmp_path: Path, slug: str) -> Path:
    profile_dir = tmp_path / ".hermes" / "profiles" / slug
    profile_dir.mkdir(parents=True)
    for name in ("CLAUDE.md", "SOUL.md", "USER.md", "MEMORY.md", "manifest.json"):
        (profile_dir / name).write_text(f"{slug} {name}\n", encoding="utf-8")
    (profile_dir / ".env").write_text("K=v\n", encoding="utf-8")
    return tmp_path / ".hermes"


def _make_agents_repo(tmp_path: Path) -> Path:
    source = tmp_path / "agents" / "hermes" / "profiles" / "atlas-ceo"
    source.mkdir(parents=True)
    for name in ("CLAUDE.md", "SOUL.md", "USER.md", "MEMORY.md", "manifest.json"):
        (source / name).write_text(f"atlas-ceo {name}\n", encoding="utf-8")
    eval_dir = source / "eval" / "fixtures"
    eval_dir.mkdir(parents=True)
    (eval_dir / "fleet-source-packet.json").write_text("{}", encoding="utf-8")
    return tmp_path / "agents"


def _make_usage_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "usage.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE daily_summaries (
                date TEXT,
                provider TEXT,
                model TEXT,
                total_tokens INTEGER,
                total_cost_usd REAL
            )
            """
        )
        conn.execute(
            "INSERT INTO daily_summaries VALUES (?, ?, ?, ?, ?)",
            ("2026-05-14", "openrouter", "cheap", 123, 0.0),
        )
    return db_path


def _write_buffer(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO messages (role, content, created_at) VALUES (?, ?, ?)",
            ("user", "private Slack sentence", 1780000000.0),
        )


def _profile(hermes_home: Path, slug: str) -> Profile:
    pdir = hermes_home / "profiles" / slug
    return Profile(
        slug=slug,
        model="x/y",
        provider="openrouter",
        soul_md_path=pdir / "SOUL.md",
        user_md_path=pdir / "USER.md",
        memory_md_path=pdir / "MEMORY.md",
        env_path=pdir / ".env",
    )


def _proposal_args() -> dict[str, object]:
    return {
        "title": "Approve Atlas weekly operating focus",
        "summary": "Atlas found too many competing priorities.",
        "recommendation": "Approve one weekly operating focus.",
        "decision_kind": "approve_action",
        "priority": "high",
        "horizon": "7d",
        "risk_level": "medium",
        "reversibility": "easy",
        "upside": "Keeps Alex focused on the highest-leverage work.",
        "downside": "Lower-priority cleanup waits another cycle.",
        "next_action": "Approve the proposed focus.",
        "confidence": 0.8,
        "source_packet_ref": "fixture source packet",
        "model_route": "anthropic:claude-sonnet-4-6",
        "model_route_status": "premium",
        "model_route_degraded": False,
        "evidence": [
            {
                "label": "Recent Atlas planning run",
                "source_type": "run",
                "href": "/observability",
                "confidence": 0.9,
            }
        ],
    }


def _follow_up_args() -> dict[str, object]:
    return {
        "source_follow_up_event_id": "queued-event-1",
        "source_action_id": "action-1",
        "approved_decision_title": "Approve Atlas weekly operating focus",
        "next_action": "Alex confirms the operating focus.",
        "watch_item": "Watch whether pending decisions shrink.",
        "non_action": "Do not dispatch or execute work.",
        "review_timing": "Review in 24h.",
        "confidence": 0.82,
    }


def builtin_tools_for_profile_with_names(profile: Profile, names: list[str]):
    (profile.env_path.parent / "config.yaml").write_text(
        "tools:\n  builtin:\n" + "".join(f"    - {name}\n" for name in names),
        encoding="utf-8",
    )
    return builtin_tools_for_profile(profile)
