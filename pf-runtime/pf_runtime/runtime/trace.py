"""Session tracing — structured stdout + optional Langfuse."""
from __future__ import annotations

import json
import logging
import os
import time
from decimal import Decimal

_log = logging.getLogger(__name__)


def emit_session_trace(
    *,
    profile_slug: str,
    session_id: str,
    model: str,
    latency_ms: float,
    finish_reason: str,
    cost_usd: Decimal,
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
