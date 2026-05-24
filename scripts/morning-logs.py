#!/usr/bin/env python3
"""Morning Logs v0.1 — read-only Hermes operational briefing.

Collects dashboard/runtime truth, writes one local Markdown report, and emits
one safe Hermes -> PFOS event. No write actions, no approval execution, no
token edits, no process control.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from hermes.lib.agent_events import EmitError, emit_event  # noqa: E402

HERMES_BASE_URL = os.environ.get("HERMES_DASHBOARD_URL", "http://127.0.0.1:9119")
HERMES_PROFILE_HOME = Path(
    os.environ.get("HERMES_PERSONAL_PROFILE_HOME", "~/.hermes/profiles/personal")
).expanduser()
OUTBOX = ROOT / "_inbox" / "morning-logs"
PROFILE_DIR = ROOT / "hermes" / "profiles" / "morning-logs"
TOKEN_ENV = Path("~/.config/prettyfly-marketing/hermes-tokens.env").expanduser()
API_USAGE_LATEST = Path("~/.api-usage/latest.json").expanduser()

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9\-]{12,}"),
    re.compile(r"(?i)(token|secret|api[_-]?key|authorization)(=|:)\s*[^,\s]+"),
    re.compile(r"(?i)(credentials|secrets|memory-vault-private)/[^,\s)]+"),
)


def redact(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    return redacted


def dashboard_token() -> str | None:
    if os.environ.get("HERMES_DASHBOARD_SESSION_TOKEN"):
        return os.environ["HERMES_DASHBOARD_SESSION_TOKEN"]
    try:
        html = urllib.request.urlopen(f"{HERMES_BASE_URL}/", timeout=5).read().decode("utf-8")
    except Exception:
        return None
    match = re.search(r'__HERMES_SESSION_TOKEN__="([^"]+)"', html)
    return match.group(1) if match else None


def get_json(path: str, *, protected: bool = False) -> Any:
    headers: dict[str, str] = {}
    if protected:
        token = dashboard_token()
        if token:
            headers["X-Hermes-Session-Token"] = token
    req = urllib.request.Request(f"{HERMES_BASE_URL}{path}", headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def safe_get(path: str, *, protected: bool = False) -> dict[str, Any]:
    try:
        return {"ok": True, "value": get_json(path, protected=protected)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}"}
    except Exception as exc:
        return {"ok": False, "error": redact(str(exc))}


def run_git(repo: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=str(repo),
            check=False,
            capture_output=True,
            text=True,
            timeout=8,
        )
        return redact((result.stdout or result.stderr).strip())
    except subprocess.TimeoutExpired:
        return "git command timed out"


def repo_signal() -> list[dict[str, Any]]:
    repos = [
        ROOT,
        Path("~/Projects/prettyfly-os").expanduser(),
        Path("~/Projects/memory-vault").expanduser(),
        Path("~/Projects/house-of-vibe").expanduser(),
    ]
    out: list[dict[str, Any]] = []
    for repo in repos:
        if not (repo / ".git").exists():
            continue
        status = run_git(repo, ["status", "--short", "--branch"])
        lines = [line for line in status.splitlines() if line]
        branch = lines[0] if lines else "## unknown"
        dirty = [line for line in lines[1:] if line]
        out.append(
            {
                "name": repo.name,
                "path": str(repo),
                "branch": branch,
                "dirty_count": len(dirty),
                "recent_commit": run_git(repo, ["log", "-1", "--oneline"]),
            }
        )
    return out


def log_signal() -> dict[str, Any]:
    files = ("agent", "gateway")
    summary: dict[str, Any] = {}
    for name in files:
        result = safe_get(f"/api/logs?file={name}&lines=200", protected=True)
        if not result["ok"]:
            summary[name] = {"available": False, "error": result["error"]}
            continue
        payload = result.get("value") or {}
        raw = json.dumps(payload)
        summary[name] = {
            "available": True,
            "error_count": len(re.findall(r"\b(ERROR|FAILED|CRITICAL)\b", raw, re.I)),
            "warning_count": len(re.findall(r"\b(WARN|WARNING)\b", raw, re.I)),
        }
    return summary


def api_usage_signal() -> dict[str, Any]:
    if not API_USAGE_LATEST.exists():
        return {
            "available": False,
            "error": f"missing {API_USAGE_LATEST}",
        }
    try:
        data = json.loads(API_USAGE_LATEST.read_text())
    except Exception as exc:
        return {"available": False, "error": redact(str(exc))}

    totals = data.get("totals") if isinstance(data.get("totals"), dict) else {}
    providers = data.get("providers") if isinstance(data.get("providers"), list) else []
    degraded = [
        str(provider.get("provider"))
        for provider in providers
        if isinstance(provider, dict)
        and provider.get("status") in {"degraded", "failed", "error", "low-balance"}
        and provider.get("provider")
    ]
    low_balance = [
        str(provider.get("provider"))
        for provider in providers
        if isinstance(provider, dict)
        and provider.get("status") == "low-balance"
        and provider.get("provider")
    ]

    return {
        "available": True,
        "generated_at": data.get("generated_at"),
        "today_usd": float(totals.get("today_usd") or 0),
        "mtd_usd": float(totals.get("mtd_usd") or 0),
        "warning_count": as_int(data.get("warning_count")),
        "manual_review_overdue_count": as_int(data.get("manual_review_overdue_count")),
        "degraded_providers": degraded[:8],
        "low_balance_providers": low_balance[:8],
        "artifact_path": data.get("artifact_path"),
    }


def collect() -> dict[str, Any]:
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "dashboard": {
            "docs": safe_get("/openapi.json"),
            "status": safe_get("/api/status"),
        },
        "fleet": {
            "ops": safe_get("/api/plugins/prettyfly-fleet/ops/status"),
            "profiles": safe_get("/api/plugins/prettyfly-fleet/profiles"),
            "approvals": safe_get("/api/plugins/prettyfly-fleet/approvals/pending"),
            "events": safe_get("/api/plugins/prettyfly-fleet/events/recent?limit=10"),
            "crons": safe_get("/api/plugins/prettyfly-fleet/crons"),
        },
        "labyrinth": {
            "health": safe_get("/api/plugins/hermes-labyrinth/health"),
            "guideposts": safe_get("/api/plugins/hermes-labyrinth/guideposts"),
        },
        "knowledge_vault": {
            "status": safe_get("/api/plugins/knowledge-vault/status"),
            "retrieval": safe_get("/api/plugins/knowledge-vault/retrieval"),
            "memory_health": safe_get("/api/plugins/knowledge-vault/memory-health"),
        },
        "runtime": {
            "gateway_state_file_exists": (HERMES_PROFILE_HOME / "gateway_state.json").exists(),
            "logs": log_signal(),
        },
        "api_usage": api_usage_signal(),
        "repos": repo_signal(),
    }


def val(snapshot: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = snapshot
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def summarize_knowledge(snapshot: dict[str, Any]) -> dict[str, Any]:
    status = val(snapshot, "knowledge_vault", "status", default={})
    retrieval = val(snapshot, "knowledge_vault", "retrieval", default={})
    memory_health = val(snapshot, "knowledge_vault", "memory_health", default={})

    status_value = status.get("value") if status.get("ok") else {}
    retrieval_value = retrieval.get("value") if retrieval.get("ok") else {}
    memory_health_value = memory_health.get("value") if memory_health.get("ok") else {}
    freshness = status_value.get("freshness") if isinstance(status_value, dict) else {}
    health_snapshot = (
        memory_health_value.get("snapshot") if isinstance(memory_health_value, dict) else {}
    ) or {}

    blockers_count = as_int(health_snapshot.get("blockers_count"))
    warnings_count = as_int(health_snapshot.get("warnings_count"))
    strict_wiki_blockers = [
        redact(item)
        for item in (health_snapshot.get("strict_wiki_blockers") or [])[:3]
        if isinstance(item, str)
    ]
    freshness_failures = freshness.get("failures") or [] if isinstance(freshness, dict) else []
    freshness_warnings = freshness.get("warnings") or [] if isinstance(freshness, dict) else []

    out = {
        "status_available": bool(status.get("ok")),
        "retrieval_available": bool(retrieval.get("ok")),
        "memory_health_available": bool(memory_health.get("ok")),
        "status_error": status.get("error"),
        "retrieval_error": retrieval.get("error"),
        "memory_health_error": memory_health.get("error"),
        "freshness_ok": bool(freshness.get("ok")) if isinstance(freshness, dict) else False,
        "freshness_failure_count": len(freshness_failures),
        "freshness_warning_count": len(freshness_warnings),
        "freshness_warnings": [redact(str(item)) for item in freshness_warnings[:3]],
        "retrieval_ok": bool(retrieval_value.get("ok")) if isinstance(retrieval_value, dict) else False,
        "retrieval_passed": retrieval_value.get("passed") if isinstance(retrieval_value, dict) else None,
        "retrieval_total": retrieval_value.get("total") if isinstance(retrieval_value, dict) else None,
        "retrieval_failed": retrieval_value.get("failed") if isinstance(retrieval_value, dict) else None,
        "memory_health_verdict": health_snapshot.get("verdict") or "unavailable",
        "memory_blockers_count": blockers_count,
        "memory_warnings_count": warnings_count,
        "strict_wiki_blocker_count": len(strict_wiki_blockers),
        "strict_wiki_blockers": strict_wiki_blockers,
    }
    out["memory_trustworthy"] = (
        out["status_available"]
        and out["retrieval_available"]
        and out["memory_health_available"]
        and out["freshness_ok"]
        and out["retrieval_ok"]
        and blockers_count == 0
    )
    return out


def summarize(snapshot: dict[str, Any]) -> dict[str, Any]:
    status = val(snapshot, "dashboard", "status", "value", default={})
    ops = val(snapshot, "fleet", "ops", "value", default={})
    approvals = val(snapshot, "fleet", "approvals", "value", "approvals", default=[])
    events = val(snapshot, "fleet", "events", "value", "events", default=[])
    guideposts = val(snapshot, "labyrinth", "guideposts", "value", "guideposts", default=[])
    lab_health = val(snapshot, "labyrinth", "health", "value", default={})
    repos = snapshot.get("repos") or []
    log_summary = val(snapshot, "runtime", "logs", default={})
    api_usage = val(snapshot, "api_usage", default={})
    knowledge = summarize_knowledge(snapshot)

    platform_errors = []
    for name, platform in (ops.get("platforms") or {}).items():
        if platform.get("error_message") or platform.get("state") not in (None, "connected", "running"):
            platform_errors.append(f"{name}: {platform.get('error_message') or platform.get('state')}")

    warnings = [
        gp for gp in guideposts if gp.get("severity") in {"warning", "error", "critical"}
    ]
    log_error_count = sum(int(v.get("error_count", 0)) for v in log_summary.values() if isinstance(v, dict))
    dirty_repos = [repo for repo in repos if repo.get("dirty_count", 0) > 0]
    gateway_running = bool(ops.get("gateway_running") or status.get("gateway_running"))
    usable = gateway_running and not platform_errors and bool(lab_health.get("ok"))

    if not gateway_running:
        next_action = "Gateway is not running; open Fleet, then Logs, before any workflow work."
    elif platform_errors:
        next_action = "Resolve the platform failure shown in Fleet before approving work."
    elif not knowledge["status_available"]:
        next_action = f"Open Knowledge Vault; status route is unavailable ({knowledge['status_error']})."
    elif not knowledge["freshness_ok"]:
        next_action = "Open Knowledge Vault freshness and inspect failed index signals."
    elif not knowledge["retrieval_available"]:
        next_action = f"Open Knowledge Vault; retrieval route is unavailable ({knowledge['retrieval_error']})."
    elif not knowledge["retrieval_ok"]:
        next_action = "Open Knowledge Vault retrieval; golden-query regression is present."
    elif not knowledge["memory_health_available"]:
        next_action = (
            f"Open Knowledge Vault; memory-health route is unavailable "
            f"({knowledge['memory_health_error']})."
        )
    elif knowledge["memory_blockers_count"]:
        next_action = "Open Knowledge Vault memory health and review blockers before trusting memory."
    elif approvals:
        oldest = max(approvals, key=lambda item: float(item.get("age_hours", 0)))
        next_action = (
            f"Review oldest pending approval: {oldest.get('agent_slug')} "
            f"{oldest.get('skill_slug')} ({oldest.get('age_hours')}h)."
        )
    elif warnings:
        next_action = "Open Labyrinth guideposts and inspect the warning journey."
    elif log_error_count:
        next_action = "Open Logs after Labyrinth; recent runtime errors are present."
    elif api_usage.get("available") and api_usage.get("manual_review_overdue_count", 0):
        next_action = "Open the API usage dashboard and clear overdue manual provider reviews."
    elif api_usage.get("available") and api_usage.get("warning_count", 0):
        next_action = "Open the API usage dashboard before running expensive research paths."
    else:
        next_action = ops.get("recommended_next_action") or "Hermes is usable; continue with the morning operating loop."

    broken = []
    if not gateway_running:
        broken.append("gateway not running")
    broken.extend(platform_errors)
    if not knowledge["status_available"]:
        broken.append(f"Knowledge Vault status unavailable: {knowledge['status_error']}")
    elif not knowledge["freshness_ok"]:
        broken.append(f"Knowledge Vault freshness has {knowledge['freshness_failure_count']} failure(s)")
    if not knowledge["retrieval_available"]:
        broken.append(f"Knowledge Vault retrieval unavailable: {knowledge['retrieval_error']}")
    elif not knowledge["retrieval_ok"]:
        broken.append(
            f"Knowledge Vault retrieval failed "
            f"({knowledge['retrieval_passed']}/{knowledge['retrieval_total']})"
        )
    if not knowledge["memory_health_available"]:
        broken.append(f"Knowledge Vault memory health unavailable: {knowledge['memory_health_error']}")
    elif knowledge["memory_blockers_count"]:
        broken.append(f"Memory health has {knowledge['memory_blockers_count']} blocker(s)")
    if warnings:
        broken.append(f"{len(warnings)} Labyrinth warning/error guidepost(s)")
    if log_error_count:
        broken.append(f"{log_error_count} recent runtime error marker(s)")
    if not api_usage.get("available"):
        broken.append(f"API usage status unavailable: {api_usage.get('error', 'unknown')}")
    elif api_usage.get("warning_count", 0):
        broken.append(f"API usage has {api_usage.get('warning_count')} warning(s)")
    elif api_usage.get("manual_review_overdue_count", 0):
        broken.append(
            f"API usage has {api_usage.get('manual_review_overdue_count')} manual review(s) overdue"
        )

    return {
        "usable": usable,
        "gateway_state": ops.get("gateway_state") or status.get("gateway_state") or "unknown",
        "gateway_running": gateway_running,
        "platform_errors": platform_errors,
        "approval_count": len(approvals),
        "oldest_approval": max(approvals, key=lambda item: float(item.get("age_hours", 0))) if approvals else None,
        "recent_event_count": len(events),
        "guidepost_count": len(guideposts),
        "guidepost_warning_count": len(warnings),
        "dirty_repo_count": len(dirty_repos),
        "log_error_count": log_error_count,
        "api_usage_available": bool(api_usage.get("available")),
        "api_usage_today_usd": float(api_usage.get("today_usd") or 0),
        "api_usage_mtd_usd": float(api_usage.get("mtd_usd") or 0),
        "api_usage_warning_count": as_int(api_usage.get("warning_count")),
        "api_usage_manual_review_overdue_count": as_int(api_usage.get("manual_review_overdue_count")),
        "api_usage_degraded_providers": api_usage.get("degraded_providers") or [],
        "api_usage_low_balance_providers": api_usage.get("low_balance_providers") or [],
        "api_usage_artifact_path": api_usage.get("artifact_path"),
        **knowledge,
        "broken": broken,
        "recommended_next_action": next_action,
    }


def render_report(snapshot: dict[str, Any], summary: dict[str, Any], report_path: Path) -> str:
    repos = snapshot.get("repos") or []
    approvals = val(snapshot, "fleet", "approvals", "value", "approvals", default=[])
    guideposts = val(snapshot, "labyrinth", "guideposts", "value", "guideposts", default=[])
    openapi = val(snapshot, "dashboard", "docs", "value", default={})
    path_count = len(openapi.get("paths", {})) if isinstance(openapi, dict) else 0

    lines = [
        "---",
        "profile: morning-logs",
        "skill: daily-brief",
        f"generated_at: {snapshot['generated_at']}",
        "proposal_status: proposed",
        "private_payload_redacted: true",
        "---",
        "",
        f"# Morning Logs — {report_path.stem}",
        "",
        "## Operator Answer",
        "",
        f"- Hermes usable right now: {'yes' if summary['usable'] else 'no'}",
        f"- Memory trustworthy today: {'yes' if summary['memory_trustworthy'] else 'no'}",
        f"- Gateway: {summary['gateway_state']} (running: {str(summary['gateway_running']).lower()})",
        f"- Broken: {', '.join(summary['broken']) if summary['broken'] else 'nothing blocking in the collected signals'}",
        f"- Needs Alex: {summary['approval_count']} pending approval(s)",
        f"- Recommended next action: {summary['recommended_next_action']}",
        "",
        "## Dashboard Loop",
        "",
        "1. Fleet — confirm gateway, approvals, profile roster, and next action.",
        "2. Knowledge Vault — confirm memory freshness, retrieval, and memory-health blockers.",
        "3. Labyrinth — inspect warning guideposts and failed/long journeys.",
        "4. Sessions — open the run transcript only when Labyrinth points there.",
        "5. Logs — inspect raw runtime failures only after Fleet/Labyrinth point there.",
        "6. Cron — confirm Morning Logs schedule and last run.",
        "7. Profiles — verify the responsible profile identity and scope.",
        "8. Config / Keys — use only for setup or broken credentials.",
        "9. Docs — map the API surface for the next narrow slice.",
        "",
        "## Fleet",
        "",
        f"- Pending approvals: {summary['approval_count']}",
        f"- Recent events sampled: {summary['recent_event_count']}",
        f"- OpenAPI paths visible from `/docs`: {path_count}",
    ]

    oldest = summary.get("oldest_approval")
    if oldest:
        lines.append(
            "- Oldest approval: "
            f"{oldest.get('agent_slug')} / {oldest.get('skill_slug')} "
            f"({oldest.get('age_hours')}h, {oldest.get('type')})"
        )

    lines.extend(["", "## Knowledge Vault", ""])
    retrieval_result = "unknown"
    if summary["retrieval_passed"] is not None and summary["retrieval_total"] is not None:
        retrieval_result = f"{summary['retrieval_passed']}/{summary['retrieval_total']}"
    lines.extend(
        [
            f"- Freshness ok: {str(summary['freshness_ok']).lower()} "
            f"({summary['freshness_warning_count']} warning(s), "
            f"{summary['freshness_failure_count']} failure(s))",
            f"- Retrieval eval: {retrieval_result} "
            f"({summary['retrieval_failed'] if summary['retrieval_failed'] is not None else 'unknown'} failed)",
            f"- Memory health: {summary['memory_health_verdict']} "
            f"({summary['memory_blockers_count']} blocker(s), "
            f"{summary['memory_warnings_count']} warning(s))",
            "- Guardrails: read-only; no reindex, repair, note edit, private vault access, or profile memory-provider mutation.",
        ]
    )
    for warning in summary["freshness_warnings"]:
        lines.append(f"- Freshness warning: {warning}")
    for blocker in summary["strict_wiki_blockers"]:
        lines.append(f"- Strict-wiki blocker: {blocker}")

    lines.extend(["", "## API Usage", ""])
    lines.extend(
        [
            f"- Status available: {str(summary['api_usage_available']).lower()}",
            f"- API-billed today: ${summary['api_usage_today_usd']:.2f}",
            f"- API-billed MTD: ${summary['api_usage_mtd_usd']:.2f}",
            f"- Warnings: {summary['api_usage_warning_count']}",
            f"- Manual reviews overdue: {summary['api_usage_manual_review_overdue_count']}",
            "- Degraded providers: "
            f"{', '.join(summary['api_usage_degraded_providers']) if summary['api_usage_degraded_providers'] else 'none'}",
            "- Low-balance providers: "
            f"{', '.join(summary['api_usage_low_balance_providers']) if summary['api_usage_low_balance_providers'] else 'none'}",
        ]
    )
    if summary["api_usage_artifact_path"]:
        lines.append(f"- Operator dashboard: {summary['api_usage_artifact_path']}")

    lines.extend(["", "## Labyrinth", ""])
    lines.append(f"- Guideposts: {summary['guidepost_count']}")
    lines.append(f"- Warning/error guideposts: {summary['guidepost_warning_count']}")
    for gp in guideposts[:5]:
        lines.append(
            f"- {gp.get('severity', 'info')}: {gp.get('title', 'untitled')} "
            f"({gp.get('kind', 'unknown')})"
        )

    lines.extend(["", "## Repos", ""])
    for repo in repos:
        lines.append(
            f"- {repo['name']}: {repo['branch']}; dirty files: {repo['dirty_count']}; "
            f"latest: {repo['recent_commit']}"
        )

    lines.extend(
        [
            "",
            "## Safety",
            "",
            "- This run did not kill processes, edit tokens, execute approvals, deploy, purchase, or modify repo files.",
            "- PFOS event emission uses only a redacted evidence payload with counts and this report path.",
        ]
    )
    return "\n".join(lines) + "\n"


def load_event_env() -> None:
    if os.environ.get("HERMES_AGENT_EVENTS_TOKEN") or not TOKEN_ENV.exists():
        return
    for line in TOKEN_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").strip()
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if key.strip() in {"HERMES_AGENT_EVENTS_TOKEN", "HERMES_AGENT_EVENTS_URL"}:
            os.environ.setdefault(key.strip(), value)


def write_outputs(snapshot: dict[str, Any], report: str, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report)
    state_path = report_path.parent / "latest-snapshot.json"
    state_path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n")


def emit_summary(summary: dict[str, Any], report_path: Path, *, dry_run: bool) -> dict[str, Any]:
    load_event_env()
    rel_report = report_path.relative_to(ROOT).as_posix()
    return emit_event(
        PROFILE_DIR,
        "morning_logs.report.propose",
        {
            "trace_id": report_path.stem,
            "confidence": 0.8 if summary["usable"] else 0.65,
            "data": {
                "readout_path": rel_report,
                "decision": "continue" if summary["usable"] else "inspect",
                "gateway_state": summary["gateway_state"],
                "approval_count": summary["approval_count"],
                "guidepost_warning_count": summary["guidepost_warning_count"],
                "dirty_repo_count": summary["dirty_repo_count"],
                "log_error_count": summary["log_error_count"],
                "memory_trustworthy": summary["memory_trustworthy"],
                "knowledge_freshness_ok": summary["freshness_ok"],
                "knowledge_retrieval_ok": summary["retrieval_ok"],
                "knowledge_retrieval_passed": summary["retrieval_passed"],
                "knowledge_retrieval_total": summary["retrieval_total"],
                "memory_health_verdict": summary["memory_health_verdict"],
                "memory_blockers_count": summary["memory_blockers_count"],
                "memory_warnings_count": summary["memory_warnings_count"],
                "api_usage_available": summary["api_usage_available"],
                "api_usage_today_usd": summary["api_usage_today_usd"],
                "api_usage_mtd_usd": summary["api_usage_mtd_usd"],
                "api_usage_warning_count": summary["api_usage_warning_count"],
                "api_usage_manual_review_overdue_count": summary[
                    "api_usage_manual_review_overdue_count"
                ],
                "recommended_next_action": summary["recommended_next_action"],
            },
        },
        dry_run=dry_run,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Morning Logs v0.1.")
    parser.add_argument("--date", help="YYYY-MM-DD report date; defaults to today local time")
    parser.add_argument(
        "--emit",
        action="store_true",
        help="Opt-in: also emit the legacy PFOS event. Default is local receipt only "
        "(per 2026-05-23-deprecate-pfos-emitter-from-profile-doctrine.md).",
    )
    parser.add_argument("--emit-dry-run", action="store_true", help="Build event payload without POSTing")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_date = args.date or dt.datetime.now().strftime("%Y-%m-%d")
    report_path = OUTBOX / f"{report_date}-morning-logs.md"
    snapshot = collect()
    summary = summarize(snapshot)
    report = render_report(snapshot, summary, report_path)
    write_outputs(snapshot, report, report_path)

    result: dict[str, Any] | None = None
    if args.emit:
        try:
            result = emit_summary(summary, report_path, dry_run=args.emit_dry_run)
        except EmitError as exc:
            print(f"event_emit_failed: {redact(str(exc))}", file=sys.stderr)

    print(json.dumps({"report_path": str(report_path), "summary": summary, "event": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
