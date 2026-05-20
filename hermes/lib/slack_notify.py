"""Slack notification helper for fleet decision events.

Posts a Slack DM via the existing Hermes send_message tool with a footer
that invites emoji-reaction approvals. The paired poll-slack-approvals.py
script polls reactions and updates agent_events.status accordingly.

Requires SLACK_BOT_TOKEN + SLACK_APP_TOKEN env vars (same as Atlas's
existing Slack DM config). If tokens are missing, notify_decision logs
the failure but does NOT raise — the upstream skill should still complete
successfully even when the Slack DM can't be sent.

Approval mapping (mirrored by poll-slack-approvals.py):
  ✅ → status='approved'
  ✏️ → status='revise'
  ❌ → status='rejected'
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Path to Hermes runtime so we can import send_message_tool.
_HERMES_HOME = Path(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")))
_HERMES_AGENT = _HERMES_HOME / "hermes-agent"
if _HERMES_AGENT.is_dir() and str(_HERMES_AGENT) not in sys.path:
    sys.path.insert(0, str(_HERMES_AGENT))


APPROVAL_FOOTER = "React ✅ approve · ✏️ revise · ❌ kill"


def notify_decision(message_text: str, agent_event_id: str, slack_user: Optional[str] = None) -> Optional[str]:
    """Post a decision-requires-approval DM to Alex's Slack.

    Args:
        message_text: The decision summary to post (2-4 lines max).
        agent_event_id: The PFOS agent_events row UUID — embedded in the
            message footer so the poller can correlate reactions back to rows.
        slack_user: Override the recipient (defaults to env SLACK_DM_RECIPIENT
            or 'alex'). Use Slack user ID (U...) ideally; DM-resolve falls
            back to user-name resolution per send_message_tool.

    Returns:
        Slack message timestamp on success, None on any failure (token
        missing, network error, scope error). Failure is logged but never
        raises — upstream skill completes successfully even without the DM.
    """
    recipient = slack_user or os.environ.get("SLACK_DM_RECIPIENT", "alex")
    bot_token = os.environ.get("SLACK_BOT_TOKEN")

    if not bot_token:
        logger.warning(
            "SLACK_BOT_TOKEN not set — slack_notify.notify_decision skipped (agent_event_id=%s)",
            agent_event_id,
        )
        return None

    full_message = (
        f"{message_text}\n\n"
        f"---\n"
        f"_{APPROVAL_FOOTER}_\n"
        f"_event:{agent_event_id}_"
    )

    try:
        from tools.send_message_tool import send_message  # type: ignore
    except ImportError as exc:
        logger.warning("send_message tool unavailable (%s) — DM skipped", exc)
        return None

    try:
        result = send_message(
            platform="slack",
            recipient=recipient,
            message=full_message,
        )
        # send_message returns a JSON string on success per its contract
        import json
        parsed = json.loads(result) if isinstance(result, str) else result
        ts = parsed.get("ts") or parsed.get("message_ts") or None
        if ts:
            logger.info("slack_notify posted (ts=%s, event=%s)", ts, agent_event_id)
        return ts
    except Exception as exc:  # noqa: BLE001 — intentional broad catch; never raise
        logger.warning("slack_notify failed (%s) — DM skipped", exc)
        return None


if __name__ == "__main__":
    # Smoke test: python3 -m hermes.lib.slack_notify "test message" fake-uuid-123
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("message")
    p.add_argument("event_id")
    p.add_argument("--recipient", default=None)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO)
    ts = notify_decision(args.message, args.event_id, slack_user=args.recipient)
    print(f"ts={ts}")
