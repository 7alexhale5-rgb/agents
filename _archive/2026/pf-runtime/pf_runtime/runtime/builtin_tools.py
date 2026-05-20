"""Config-driven built-in tools for PF Runtime.

Built-ins are intentionally small and profile-gated. They let a profile opt in
to read-only local capabilities without granting broad mutation authority.
"""
from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar, cast
from urllib.parse import urlparse

from pf_runtime.config import Profile
from pf_runtime.runtime.tool_dispatch import Tool, ToolContext, ToolResult

try:  # pragma: no cover - exercised when PyYAML is installed
    import yaml
except Exception:  # pragma: no cover
    yaml = None  # type: ignore[assignment]


def builtin_tools_for_profile(profile: Profile) -> list[Tool]:
    """Return built-in tools enabled by ``config.yaml`` for *profile*."""
    names = _enabled_builtin_tool_names(profile.env_path.parent / "config.yaml")
    tools: list[Tool] = []
    if "fleet.snapshot" in names:
        tools.append(FleetSnapshotTool(profile=profile))
    if "business.scorecard.snapshot" in names:
        tools.append(BusinessScorecardSnapshotTool(profile=profile))
    if "atlas.propose_action" in names:
        tools.append(AtlasProposeActionTool(profile=profile))
    if "atlas.record_follow_up" in names:
        tools.append(AtlasRecordFollowUpTool(profile=profile))
    return tools


def _enabled_builtin_tool_names(config_path: Path) -> set[str]:
    if not config_path.exists():
        return set()
    text = config_path.read_text(encoding="utf-8")
    if yaml is not None:
        data = yaml.safe_load(text) or {}
        builtin = (data.get("tools") or {}).get("builtin") or []
        return {item for item in builtin if isinstance(item, str)}

    names: set[str] = set()  # type: ignore[unreachable]
    in_tools = False
    in_builtin = False
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not line.startswith(" ") and stripped.endswith(":"):
            in_tools = stripped == "tools:"
            in_builtin = False
            continue
        if in_tools and stripped == "builtin:":
            in_builtin = True
            continue
        if in_tools and in_builtin and stripped.startswith("- "):
            names.add(stripped[2:].strip())
    return names


class FleetSnapshotTool(Tool):
    """Read-only source packet for Atlas CEO briefs."""

    name = "fleet.snapshot"
    description = (
        "Read-only compact fleet source packet: profile sync health, runtime "
        "buffer counts, local API usage costs, Atlas eval inventory, freshness, "
        "confidence, and missing-signal notes. Never returns secrets or raw "
        "private message text."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "profile_limit": {
                "type": "integer",
                "description": "Maximum profile sync rows to include.",
            },
            "period_days": {
                "type": "integer",
                "description": "Lookback window for PFOS source packet.",
            }
        },
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        profile: Profile,
        agents_repo: Path | None = None,
        api_usage_db: Path | None = None,
    ) -> None:
        self._profile = profile
        self._agents_repo = agents_repo or Path(
            os.environ.get("PF_AGENTS_REPO", "/Users/alexhale/Projects/agents")
        )
        self._api_usage_db = api_usage_db or Path.home() / ".api-usage" / "usage.db"

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        profile_limit = int(args.get("profile_limit") or 20)
        period_days = int(args.get("period_days") or 7)
        packet = await self.source_packet(
            profile_limit=profile_limit,
            period_days=period_days,
        )
        return ToolResult(ok=True, output=packet)

    async def source_packet(self, *, profile_limit: int = 20, period_days: int = 7) -> dict[str, Any]:
        pfos_packet = await _fetch_pfos_source_packet(
            env_path=self._profile.env_path,
            agent_slug=self._profile.slug,
            period_days=period_days,
        )
        if pfos_packet["ok"]:
            output = cast(dict[str, Any], pfos_packet["packet"])
            output.setdefault("tool", self.name)
            output.setdefault("source_mode", "pfos")
            return output

        packet = self.build_packet(profile_limit=profile_limit)
        missing = packet.setdefault("missing_signals", [])
        if isinstance(missing, list):
            missing.append(str(pfos_packet["error"]))
        packet["source_mode"] = "local_fallback"
        packet["tool"] = self.name
        return packet

    def build_packet(self, *, profile_limit: int = 20) -> dict[str, Any]:
        runtime_profile_dir = self._profile.env_path.parent
        runtime_profiles_dir = runtime_profile_dir.parent
        source_profiles_dir = self._agents_repo / "hermes" / "profiles"

        profile_sync = _profile_sync_packet(
            source_profiles_dir=source_profiles_dir,
            runtime_profiles_dir=runtime_profiles_dir,
            limit=profile_limit,
        )
        runtime_buffers = _runtime_buffer_packet(runtime_profiles_dir)
        costs = _cost_packet(self._api_usage_db)
        evals = _eval_packet(self._agents_repo / "hermes" / "profiles" / "atlas-ceo" / "eval")

        missing_signals: list[str] = []
        if profile_sync["missing"]:
            missing_signals.extend(profile_sync["missing"])
        if runtime_buffers["missing"]:
            missing_signals.extend(runtime_buffers["missing"])
        if costs["missing"]:
            missing_signals.extend(costs["missing"])
        if evals["missing"]:
            missing_signals.extend(evals["missing"])
        missing_signals.append(
            "PFOS source-packet endpoint unavailable; using local runtime files only."
        )

        return {
            "packet_type": "atlas.source_packet.v2",
            "generated_at": datetime.now(UTC).isoformat(),
            "agent_slug": self._profile.slug,
            "period": "local_fallback",
            "authority": "read_only",
            "source_privacy": "aggregates_only_no_secrets_no_raw_private_text",
            "sources": [
                profile_sync["source"],
                runtime_buffers["source"],
                costs["source"],
                evals["source"],
            ],
            "profile_sync": profile_sync["data"],
            "pf_runtime": runtime_buffers["data"],
            "costs": costs["data"],
            "evals": evals["data"],
            "missing_signals": sorted(set(missing_signals)),
        }


class BusinessScorecardSnapshotTool(FleetSnapshotTool):
    """Read-only business scorecard packet for Atlas."""

    name = "business.scorecard.snapshot"
    description = (
        "Read-only Atlas business scorecard source packet from PFOS: project "
        "pulse, proposal pipeline, fleet events, pending proposals, cost "
        "summary, freshness, confidence, and missing-signal notes."
    )


class AtlasProposeActionTool(Tool):
    """Write a proposed Atlas decision action to PFOS, never execute it."""

    name = "atlas.propose_action"
    description = (
        "Create a PFOS agent_actions proposal for an Atlas decision. This tool "
        "records an approval-needed proposal only; it never executes, sends, "
        "dispatches, spends, deploys, or edits production/profile files."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "silo_slug": {
                "type": "string",
                "enum": ["yeh", "koho", "ctox", "prettyfly", "rnd", "ops", "home", "fleet", "skills"],
            },
            "title": {"type": "string", "minLength": 1},
            "summary": {"type": "string", "minLength": 1},
            "recommendation": {"type": "string", "minLength": 1},
            "decision_kind": {
                "type": "string",
                "enum": ["approve_action", "choose_option", "defer", "review"],
            },
            "priority": {
                "type": "string",
                "enum": ["critical", "high", "normal", "low"],
            },
            "horizon": {
                "type": "string",
                "enum": ["now", "24h", "7d", "30d", "quarter"],
            },
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "reversibility": {
                "type": "string",
                "enum": ["easy", "moderate", "hard"],
            },
            "upside": {"type": "string", "minLength": 1},
            "downside": {"type": "string", "minLength": 1},
            "next_action": {"type": "string", "minLength": 1},
            "confidence": {"type": "number"},
            "evidence_count": {"type": "integer"},
            "source_packet_ref": {"type": "string"},
            "trace_id": {"type": "string"},
            "model_route": {"type": "string"},
            "model_route_status": {
                "type": "string",
                "enum": ["premium", "degraded", "smoke"],
            },
            "model_route_degraded": {"type": "boolean"},
            "evidence": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string", "minLength": 1},
                        "source_type": {
                            "type": "string",
                            "enum": [
                                "event",
                                "run",
                                "cost",
                                "proposal",
                                "inbox",
                                "calendar",
                                "file",
                                "web",
                                "manual",
                            ],
                        },
                        "href": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["label", "source_type"],
                    "additionalProperties": False,
                },
            },
        },
        "required": [
            "title",
            "summary",
            "recommendation",
            "decision_kind",
            "priority",
            "horizon",
            "risk_level",
            "reversibility",
            "upside",
            "downside",
            "next_action",
            "confidence",
        ],
        "additionalProperties": False,
    }

    def __init__(self, *, profile: Profile) -> None:
        self._profile = profile

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        confidence = float(args["confidence"])
        if confidence < 0 or confidence > 1:
            return ToolResult(ok=False, output=None, error="confidence_out_of_range")

        evidence = _safe_atlas_evidence(args.get("evidence"))
        evidence_count = int(args.get("evidence_count") or len(evidence))
        source_packet_ref = str(args.get("source_packet_ref") or "").strip()
        if not source_packet_ref and not evidence:
            return ToolResult(
                ok=False,
                output=None,
                error="source_packet_ref_or_evidence_required",
            )

        env = _profile_env(self._profile.env_path)
        base_url = _env_value(env, "PFOS_BASE_URL").rstrip("/")
        token = _env_value(env, "PFOS_ATLAS_ACTION_TOKEN")
        if not base_url or not token:
            return ToolResult(
                ok=False,
                output=None,
                error="pfos_atlas_action_not_configured",
            )

        silo_slug = _safe_writeback_silo(args.get("silo_slug"))
        trace_id = str(args.get("trace_id") or f"atlas-run-{context.session_id}")
        model_route = str(args.get("model_route") or "unknown")
        model_route_status = str(args.get("model_route_status") or "unknown")
        model_route_degraded = bool(args.get("model_route_degraded") is True)
        payload = {
            "action_name": "atlas.decision_proposal",
            "side_effect_class": "write",
            "params_json": {
                "schema_version": "atlas.decision_proposal.v1",
                "title": args["title"],
                "summary": args["summary"],
                "recommendation": args["recommendation"],
                "decision_kind": args["decision_kind"],
                "priority": args["priority"],
                "horizon": args["horizon"],
                "risk_level": args["risk_level"],
                "reversibility": args["reversibility"],
                "upside": args["upside"],
                "downside": args["downside"],
                "next_action": args["next_action"],
                "confidence": confidence,
                "evidence_count": evidence_count,
                "trace_id": trace_id,
                "source_packet_ref": source_packet_ref or None,
                "private_payload_redacted": True,
                "model_route": model_route,
                "model_route_status": model_route_status,
                "model_route_degraded": model_route_degraded,
                "evidence": evidence,
            },
            "confidence": confidence,
            "agent_slug": self._profile.slug,
            "trace_id": trace_id,
            "service": "atlas",
            "surface": "pf_runtime",
            "cwd_project": Path.cwd().name,
            "skill_slug": "approval-proposal-draft",
        }
        url = f"{base_url}/api/silos/{silo_slug}/agent-action"
        try:
            response = await _post_json(url, token=token, payload=payload)
        except RuntimeError as exc:
            return ToolResult(ok=False, output=None, error=str(exc))

        receipt = response.get("receipt")
        if not _verified_atlas_receipt(receipt):
            return ToolResult(ok=False, output=None, error="receipt_unverified")
        if not isinstance(receipt, dict):
            return ToolResult(ok=False, output=None, error="receipt_unverified")

        return ToolResult(
            ok=bool(response.get("ok")),
            output={
                "status": "proposed_only",
                "verified": True,
                "action_id": receipt.get("action_id"),
                "event_id": receipt.get("event_id"),
                "silo_slug": silo_slug,
                "executed": False,
                "slack_card": {
                    "action_id": receipt.get("action_id"),
                    "silo_slug": silo_slug,
                    "title": str(args["title"]),
                    "summary": str(args["summary"]),
                    "priority": str(args["priority"]),
                    "risk_level": str(args["risk_level"]),
                    "pfos_href": "/agents/atlas-ceo",
                },
            },
        )


class AtlasRecordFollowUpTool(Tool):
    """Record Atlas's approved-decision follow-up brief as a PFOS event."""

    name = "atlas.record_follow_up"
    description = (
        "Record a safe Atlas follow-up brief for an approved decision. This "
        "writes an agent_events row only; it never executes, dispatches, sends "
        "externally, spends, deploys, edits files, or creates tasks."
    )
    parameters: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "silo_slug": {
                "type": "string",
                "enum": ["yeh", "koho", "ctox", "prettyfly", "rnd", "ops", "home", "fleet", "skills"],
            },
            "source_follow_up_event_id": {"type": "string", "minLength": 1},
            "source_action_id": {"type": "string", "minLength": 1},
            "approved_decision_title": {"type": "string", "minLength": 1},
            "next_action": {"type": "string", "minLength": 1},
            "watch_item": {"type": "string", "minLength": 1},
            "non_action": {"type": "string", "minLength": 1},
            "review_timing": {"type": "string", "minLength": 1},
            "confidence": {"type": "number"},
            "trace_id": {"type": "string"},
        },
        "required": [
            "source_follow_up_event_id",
            "source_action_id",
            "approved_decision_title",
            "next_action",
            "watch_item",
            "non_action",
            "review_timing",
            "confidence",
        ],
        "additionalProperties": False,
    }

    def __init__(self, *, profile: Profile) -> None:
        self._profile = profile

    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        confidence = float(args["confidence"])
        if confidence < 0 or confidence > 1:
            return ToolResult(ok=False, output=None, error="confidence_out_of_range")

        source_follow_up_event_id = str(args.get("source_follow_up_event_id") or "").strip()
        source_action_id = str(args.get("source_action_id") or "").strip()
        if not source_follow_up_event_id or not source_action_id:
            return ToolResult(ok=False, output=None, error="source_ids_required")

        env = _profile_env(self._profile.env_path)
        url = _env_value(env, "PFOS_AGENT_EVENT_URL")
        token = _env_value(env, "PFOS_AGENT_EVENT_TOKEN")
        if not url or not token:
            return ToolResult(
                ok=False,
                output=None,
                error="pfos_agent_event_not_configured",
            )

        trace_id = str(args.get("trace_id") or f"atlas-follow-up-{context.session_id}")
        payload = {
            "type": "atlas.follow_up.ready",
            "status": "completed",
            "agent_slug": self._profile.slug,
            "surface": "pf_runtime",
            "cwd_project": Path.cwd().name,
            "skill_slug": "weekly-ceo-operating-loop",
            "trace_id": trace_id,
            "confidence": confidence,
            "data": {
                "kind": "atlas_decision_follow_up",
                "source_follow_up_event_id": source_follow_up_event_id,
                "source_action_id": source_action_id,
                "approved_decision_title": _bounded_text(args["approved_decision_title"], 240),
                "next_action": _bounded_text(args["next_action"], 500),
                "watch_item": _bounded_text(args["watch_item"], 500),
                "non_action": _bounded_text(args["non_action"], 500),
                "review_timing": _bounded_text(args["review_timing"], 160),
                "private_payload_redacted": True,
                "execution_triggered": False,
            },
        }

        try:
            response = await _post_json(url, token=token, payload=payload)
        except RuntimeError as exc:
            return ToolResult(ok=False, output=None, error=str(exc))
        if not _verified_agent_event_response(response):
            return ToolResult(ok=False, output=None, error="follow_up_event_unverified")

        return ToolResult(
            ok=True,
            output={
                "verified": True,
                "event_id": response.get("event_id"),
                "status": "completed",
                "source_follow_up_event_id": source_follow_up_event_id,
                "source_action_id": source_action_id,
                "executed": False,
            },
        )


_TRACKED_PROFILE_FILES = (
    "CLAUDE.md",
    "DOCTRINE.md",
    "SOUL.md",
    "USER.md",
    "MEMORY.md",
    "config.yaml",
    "manifest.json",
)


def _profile_sync_packet(
    *,
    source_profiles_dir: Path,
    runtime_profiles_dir: Path,
    limit: int,
) -> dict[str, Any]:
    source_names = _child_dir_names(source_profiles_dir)
    runtime_names = _child_dir_names(runtime_profiles_dir)
    names = sorted(source_names | runtime_names)
    rows: list[dict[str, Any]] = []
    missing: list[str] = []

    if not source_profiles_dir.exists():
        missing.append(f"missing source profiles dir: {source_profiles_dir}")
    if not runtime_profiles_dir.exists():
        missing.append(f"missing runtime profiles dir: {runtime_profiles_dir}")

    for name in names[: max(limit, 0)]:
        source_dir = source_profiles_dir / name
        runtime_dir = runtime_profiles_dir / name
        file_drift: list[str] = []
        for rel in _TRACKED_PROFILE_FILES:
            source_file = source_dir / rel
            runtime_file = runtime_dir / rel
            if not source_file.exists() and not runtime_file.exists():
                continue
            if source_file.exists() != runtime_file.exists():
                file_drift.append(rel)
                continue
            if source_file.is_symlink() or runtime_file.is_symlink():
                source_target = source_file.readlink() if source_file.is_symlink() else None
                runtime_target = runtime_file.readlink() if runtime_file.is_symlink() else None
                if source_target != runtime_target:
                    file_drift.append(rel)
                continue
            if source_file.read_bytes() != runtime_file.read_bytes():
                file_drift.append(rel)

        rows.append(
            {
                "profile": name,
                "source_exists": source_dir.exists(),
                "runtime_exists": runtime_dir.exists(),
                "paused": (runtime_dir / "PAUSED").exists(),
                "drift_files": file_drift[:8],
                "sync_status": "clean" if not file_drift else "drift",
            }
        )

    clean = sum(1 for row in rows if row["sync_status"] == "clean")
    stale_count = max(len(names) - len(rows), 0)
    if stale_count:
        missing.append(f"{stale_count} profile rows omitted by profile_limit")

    return {
        "source": _source_row(
            "profile_sync",
            confidence="high" if source_profiles_dir.exists() and runtime_profiles_dir.exists() else "low",
            freshness="point_in_time_filesystem_scan",
            missing=missing,
        ),
        "data": {
            "total_profiles_seen": len(names),
            "profiles_reported": len(rows),
            "clean_profiles_reported": clean,
            "drift_profiles_reported": len(rows) - clean,
            "rows": rows,
        },
        "missing": missing,
    }


def _runtime_buffer_packet(runtime_profiles_dir: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    if not runtime_profiles_dir.exists():
        missing.append(f"missing runtime profiles dir: {runtime_profiles_dir}")
    profile_dirs = sorted(runtime_profiles_dir.iterdir()) if runtime_profiles_dir.exists() else []
    for profile_dir in profile_dirs:
        if not profile_dir.is_dir():
            continue
        db_path = profile_dir / "pf_buffer.sqlite"
        if not db_path.exists():
            rows.append(
                {
                    "profile": profile_dir.name,
                    "buffer_exists": False,
                    "message_count": 0,
                    "last_message_at": None,
                }
            )
            continue
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                count, last_created = conn.execute(
                    "SELECT COUNT(*), MAX(created_at) FROM messages"
                ).fetchone()
            rows.append(
                {
                    "profile": profile_dir.name,
                    "buffer_exists": True,
                    "message_count": int(count or 0),
                    "last_message_at": _sqlite_epoch_to_iso(last_created),
                }
            )
        except sqlite3.Error as exc:
            rows.append(
                {
                    "profile": profile_dir.name,
                    "buffer_exists": True,
                    "message_count": None,
                    "last_message_at": None,
                    "error": exc.__class__.__name__,
                }
            )

    return {
        "source": _source_row(
            "pf_runtime_buffers",
            confidence="medium",
            freshness="point_in_time_sqlite_aggregate_scan",
            missing=missing,
        ),
        "data": {
            "profiles_with_buffers": sum(1 for row in rows if row["buffer_exists"]),
            "rows": rows,
        },
        "missing": missing,
    }


def _cost_packet(db_path: Path) -> dict[str, Any]:
    missing: list[str] = []
    rows: list[dict[str, Any]] = []
    if not db_path.exists():
        missing.append(f"missing local API usage DB: {db_path}")
    else:
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as conn:
                conn.row_factory = sqlite3.Row
                columns = {
                    str(row["name"])
                    for row in conn.execute("PRAGMA table_info(daily_summaries)")
                }
                if {"total_input_tokens", "total_output_tokens"} <= columns:
                    query = """
                        SELECT date, provider, model,
                               COALESCE(total_input_tokens, 0) +
                               COALESCE(total_output_tokens, 0) +
                               COALESCE(total_cache_write_tokens, 0) +
                               COALESCE(total_cache_read_tokens, 0) AS total_tokens,
                               total_cost_usd
                        FROM daily_summaries
                        ORDER BY date DESC, provider ASC, model ASC
                        LIMIT 12
                    """
                elif "total_tokens" in columns:
                    query = """
                        SELECT date, provider, model,
                               COALESCE(total_tokens, 0) AS total_tokens,
                               total_cost_usd
                        FROM daily_summaries
                        ORDER BY date DESC, provider ASC, model ASC
                        LIMIT 12
                    """
                else:
                    missing.append("daily_summaries has no token aggregate columns")
                    query = """
                        SELECT date, provider, model, 0 AS total_tokens,
                               total_cost_usd
                        FROM daily_summaries
                        ORDER BY date DESC, provider ASC, model ASC
                        LIMIT 12
                    """
                for row in conn.execute(query):
                    rows.append(
                        {
                            "date": row["date"],
                            "provider": row["provider"],
                            "model": row["model"],
                            "total_tokens": int(row["total_tokens"] or 0),
                            "total_cost_usd": float(row["total_cost_usd"] or 0.0),
                        }
                    )
        except sqlite3.Error as exc:
            missing.append(f"local API usage DB unreadable: {exc.__class__.__name__}")

    return {
        "source": _source_row(
            "local_api_usage",
            confidence="high" if rows else "low",
            freshness="latest_daily_summaries",
            missing=missing,
        ),
        "data": {"recent_daily_summaries": rows},
        "missing": missing,
    }


def _eval_packet(eval_dir: Path) -> dict[str, Any]:
    missing: list[str] = []
    files: list[dict[str, Any]] = []
    if not eval_dir.exists():
        missing.append(f"missing Atlas eval dir: {eval_dir}")
    else:
        for path in sorted(eval_dir.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".json", ".yaml", ".yml"}:
                stat = path.stat()
                files.append(
                    {
                        "path": str(path.relative_to(eval_dir)),
                        "updated_at": datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
                    }
                )
    if not files:
        missing.append("no Atlas eval/rubric files found")
    return {
        "source": _source_row(
            "atlas_evals",
            confidence="medium" if files else "low",
            freshness="point_in_time_filesystem_scan",
            missing=missing,
        ),
        "data": {"files": files[:20]},
        "missing": missing,
    }


async def _fetch_pfos_source_packet(
    *,
    env_path: Path,
    agent_slug: str,
    period_days: int,
) -> dict[str, Any]:
    env = _profile_env(env_path)
    base_url = _env_value(env, "PFOS_BASE_URL").rstrip("/")
    token = _env_value(env, "PFOS_ATLAS_SOURCE_TOKEN")
    if not base_url or not token:
        return {
            "ok": False,
            "error": "PFOS_BASE_URL/PFOS_ATLAS_SOURCE_TOKEN not configured",
        }
    period = f"{max(period_days, 1)}d"
    url = f"{base_url}/api/agents/{agent_slug}/source-packet?period={period}"
    try:
        packet = await _get_json(url, token=token)
    except RuntimeError as exc:
        return {"ok": False, "error": f"PFOS source packet unavailable: {exc}"}
    return {"ok": True, "packet": packet}


def _profile_env(env_path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if env_path.is_file():
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def _env_value(env: dict[str, str], key: str) -> str:
    return env.get(key) or os.environ.get(key, "")


def _safe_atlas_evidence(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    safe: list[dict[str, Any]] = []
    for item in value[:3]:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        source_type = str(item.get("source_type") or "").strip()
        if not label or not source_type:
            continue
        row: dict[str, Any] = {
            "label": label[:160],
            "source_type": source_type,
        }
        href = str(item.get("href") or "").strip()
        if href.startswith("/") and not href.startswith("//"):
            row["href"] = href[:240]
        else:
            row["href"] = _atlas_default_evidence_href(source_type)
        confidence = item.get("confidence")
        if isinstance(confidence, int | float) and not isinstance(confidence, bool):
            row["confidence"] = max(0.0, min(1.0, float(confidence)))
        safe.append(row)
    return safe


def _atlas_default_evidence_href(source_type: str) -> str:
    if source_type in {"event", "run"}:
        return "/observability"
    if source_type == "cost":
        return "/costs"
    if source_type == "proposal":
        return "/proposals"
    if source_type == "inbox":
        return "/inbox"
    if source_type == "calendar":
        return "/calendar"
    if source_type == "file":
        return "/files"
    if source_type == "web":
        return "/resources"
    return "/agents/atlas-ceo"


def _safe_writeback_silo(value: Any) -> str:
    allowed = {"yeh", "koho", "ctox", "prettyfly", "rnd", "ops", "home", "fleet", "skills"}
    silo = str(value or "prettyfly").strip()
    return silo if silo in allowed else "prettyfly"


def _verified_atlas_receipt(receipt: Any) -> bool:
    if not isinstance(receipt, dict):
        return False
    return (
        receipt.get("verified") is True
        and isinstance(receipt.get("action_id"), str)
        and bool(receipt.get("action_id"))
        and isinstance(receipt.get("event_id"), str)
        and bool(receipt.get("event_id"))
        and receipt.get("status") == "proposed"
        and receipt.get("executed") is False
        and receipt.get("action_name") == "atlas.decision_proposal"
    )


def _verified_agent_event_response(response: Any) -> bool:
    return (
        isinstance(response, dict)
        and response.get("ok") is True
        and isinstance(response.get("event_id"), str)
        and bool(response.get("event_id"))
    )


def _bounded_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


async def _get_json(url: str, *, token: str) -> dict[str, Any]:
    _ensure_http_url(url)

    def _sync() -> dict[str, Any]:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {token}"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
                return _read_json_response(resp, label="PFOS GET")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

    import asyncio

    return await asyncio.to_thread(_sync)


async def _post_json(
    url: str,
    *,
    token: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _ensure_http_url(url)

    def _sync() -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:  # nosec B310
                return _read_json_response(resp, label="PFOS POST")
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code}: {body_text}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

    import asyncio

    return await asyncio.to_thread(_sync)


def _ensure_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("PFOS URL must be http(s)")


def _read_json_response(resp: Any, *, label: str) -> dict[str, Any]:
    content_type = str(resp.headers.get("Content-Type", ""))
    body = resp.read().decode("utf-8", errors="replace")
    if "json" not in content_type.lower():
        kind = "auth_redirect_html" if "<html" in body[:500].lower() else "unexpected_content_type"
        raise RuntimeError(f"{label} {kind}: {content_type or 'unknown'}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} invalid_json: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} expected_json_object: {type(data).__name__}")
    return data


def _child_dir_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {child.name for child in path.iterdir() if child.is_dir()}


def _source_row(
    name: str,
    *,
    confidence: str,
    freshness: str,
    missing: list[str],
) -> dict[str, Any]:
    return {
        "name": name,
        "freshness": freshness,
        "confidence": confidence,
        "missing": missing,
    }


def _sqlite_epoch_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value), UTC).isoformat()
    except (TypeError, ValueError, OSError):
        return str(value)


def packet_to_json(packet: dict[str, Any]) -> str:
    """Stable compact JSON helper for tests and manual inspection."""
    return json.dumps(packet, sort_keys=True, separators=(",", ":"), default=str)
