"""Session tracing — structured stdout + optional Langfuse."""
from __future__ import annotations

import json
import logging
import os
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

_log = logging.getLogger(__name__)


def emit_session_trace(
    *,
    profile_slug: str,
    session_id: str,
    model: str,
    latency_ms: float,
    finish_reason: str,
    cost_usd: Decimal,
    trace_jsonl_path: Path | str | None = None,
) -> None:
    """Emit one structured log line; optionally send a Langfuse span when configured."""
    payload = {
        "kind": "pf_runtime.session",
        "ts": time.time(),
        "profile_slug": profile_slug,
        "session_id": session_id,
        "model": model,
        "latency_ms": round(latency_ms, 2),
        "finish_reason": finish_reason,
        "cost_usd": str(cost_usd),
    }
    _log.info("trace %s", json.dumps(payload, ensure_ascii=False))
    _append_jsonl(trace_jsonl_path, payload)

    public = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret = os.environ.get("LANGFUSE_SECRET_KEY", "")
    host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    if not public or not secret:
        return
    try:
        from langfuse import Langfuse

        lf = Langfuse(public_key=public, secret_key=secret, host=host)
        span = lf.start_observation(
            name="pf_runtime.session",
            as_type="chain",
            input={"profile": profile_slug},
            metadata={
                "session_id": session_id,
                "model": model,
                "latency_ms": latency_ms,
                "finish_reason": finish_reason,
                "cost_usd": str(cost_usd),
            },
        )
        span.end()
        lf.flush()
    except Exception as e:
        _log.debug("langfuse trace skipped: %s", e)


def emit_tool_trace(
    *,
    profile_slug: str,
    session_id: str,
    tool_name: str,
    tool_server: str,
    arguments_hash: str,
    success: bool,
    error_class: str,
    latency_ms: float,
    trace_jsonl_path: Path | str | None = None,
) -> None:
    """Emit a TRACE_SCHEMA-compatible tool_call line without raw arguments."""
    payload = {
        "kind": "pf_runtime.tool_call",
        "pf_runtime.profile_slug": profile_slug,
        "pf_runtime.session_id": session_id,
        "pf_runtime.span_kind": "tool_call",
        "tool.name": tool_name,
        "tool.server": tool_server,
        "tool.arguments_hash": arguments_hash,
        "tool.success": success,
        "tool.error_class": error_class,
        "latency.ms": round(latency_ms, 2),
        "ts": time.time(),
    }
    _log.info("trace %s", json.dumps(payload, ensure_ascii=False))
    _append_jsonl(trace_jsonl_path, payload)


def _append_jsonl(path: Path | str | None, payload: dict[str, Any]) -> None:
    if not path:
        return
    trace_path = Path(path).expanduser()
    try:
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
            f.write("\n")
    except Exception:
        _log.warning("trace jsonl write failed: %s", trace_path, exc_info=True)
