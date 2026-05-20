"""Slack notification helper for fleet decision events.

Two delivery paths live here side-by-side:

1. ``notify_decision`` (live) — posts a Slack DM via the existing Hermes
   send_message tool with a footer that invites emoji-reaction approvals.
   The paired ``poll-slack-approvals.py`` script polls reactions and
   updates ``agent_events.status`` accordingly. This is what the live
   fleet uses today.

2. ``notify_decision_block_kit`` (dormant) — posts an interactive Block
   Kit message with Approve / Reject / Defer buttons that fire the
   ``/api/slack/interactive`` webhook in PFOS. Webhook writes a structured
   ``approval_decision`` event back to ``agent_events`` on each click,
   skipping the polling layer. Activates when SLACK_BOT_TOKEN gains
   ``chat:write`` + the workspace adds the Interactive Components endpoint
   (see ``docs/slack-block-kit-scope-add.md`` for the steps).

Requires SLACK_BOT_TOKEN env var. If missing, both functions log + return
None — the upstream skill should still complete successfully.

Approval mapping (mirrored by poll-slack-approvals.py / interactive webhook):
  ✅ / approve_*   → status='approved'
  ✏️ / revise_*    → status='revise'
  ❌ / reject_*    → status='rejected'
"""

from __future__ import annotations

import json as _json
import logging
import os
import sys
import urllib.error
import urllib.request
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


# --------------------------------------------------------------------------- #
# Block Kit path — dormant until Slack scopes + interactive webhook land.
# --------------------------------------------------------------------------- #


def build_decision_blocks(message_text: str, agent_event_id: str) -> list[dict]:
    """Build a Block Kit message body with Approve / Reject / Defer buttons.

    The button ``value`` carries the agent_event_id back to the webhook so
    /api/slack/interactive can write a structured approval_decision event
    against the right row. ``action_id`` carries the decision verb.

    Pulled out as a pure function so callers can render the same shape
    into a dry-run preview, a unit test, or a manual ``chat.postMessage``.
    """
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message_text},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"_event: `{agent_event_id}`_"},
            ],
        },
        {
            "type": "actions",
            "block_id": f"approval:{agent_event_id}",
            "elements": [
                {
                    "type": "button",
                    "style": "primary",
                    "text": {"type": "plain_text", "text": "Approve"},
                    "action_id": "approve_decision",
                    "value": agent_event_id,
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Revise"},
                    "action_id": "revise_decision",
                    "value": agent_event_id,
                },
                {
                    "type": "button",
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Reject"},
                    "action_id": "reject_decision",
                    "value": agent_event_id,
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Reject proposal?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": "Marks this agent event `rejected`. Cannot be undone without manual SQL.",
                        },
                        "confirm": {"type": "plain_text", "text": "Reject"},
                        "deny": {"type": "plain_text", "text": "Cancel"},
                    },
                },
            ],
        },
    ]


def notify_decision_block_kit(
    message_text: str,
    agent_event_id: str,
    *,
    channel: Optional[str] = None,
) -> Optional[str]:
    """Post an interactive Block Kit DM with Approve / Reject / Defer buttons.

    Pairs with the ``/api/slack/interactive`` webhook in PFOS, which receives
    each button click, verifies the Slack signature, and updates the matching
    ``agent_events.status``. No polling.

    Currently DORMANT — does nothing useful until the bot has ``chat:write``
    and the workspace's Slack app has the Interactive Components endpoint
    configured. See ``docs/slack-block-kit-scope-add.md`` for the steps.

    Args:
        message_text: Markdown-formatted decision summary (2-4 lines).
        agent_event_id: PFOS agent_events row UUID — carried as the button
            ``value`` so the webhook can correlate clicks back to rows.
        channel: Slack channel/DM ID. Defaults to ``SLACK_DM_RECIPIENT`` env,
            falling back to ``alex``. Channel-name resolution is the caller's
            responsibility — pass a ``D...`` / ``C...`` ID for reliability.

    Returns:
        Slack message ``ts`` on success, ``None`` on any failure. Never raises.
    """
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        logger.warning(
            "SLACK_BOT_TOKEN not set — notify_decision_block_kit skipped (event=%s)",
            agent_event_id,
        )
        return None

    target_channel = channel or os.environ.get("SLACK_DM_RECIPIENT", "alex")
    blocks = build_decision_blocks(message_text, agent_event_id)
    body = _json.dumps(
        {
            "channel": target_channel,
            "text": message_text,  # accessibility/fallback for clients that can't render blocks
            "blocks": blocks,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {bot_token}",
            "Content-Type": "application/json; charset=utf-8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            parsed = _json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        logger.warning("Slack chat.postMessage failed (%s) — Block Kit DM skipped", exc)
        return None
    except (ValueError, OSError) as exc:
        logger.warning("Slack chat.postMessage parse/IO error (%s) — DM skipped", exc)
        return None

    if not parsed.get("ok"):
        # Slack returns ok=false with an error code (e.g. missing_scope,
        # channel_not_found). Log the code only — do not surface raw response
        # because misconfigured tokens can leak workspace metadata.
        logger.warning(
            "Slack chat.postMessage refused (error=%s) — event %s left pending",
            parsed.get("error", "unknown"),
            agent_event_id,
        )
        return None

    ts = parsed.get("ts")
    if ts:
        logger.info("Block Kit DM posted (ts=%s, event=%s)", ts, agent_event_id)
    return ts


if __name__ == "__main__":
    # Smoke test: python3 -m hermes.lib.slack_notify "test message" fake-uuid-123
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("message")
    p.add_argument("event_id")
    p.add_argument("--recipient", default=None)
    p.add_argument(
        "--block-kit",
        action="store_true",
        help="Use the dormant Block Kit interactive path instead of the legacy emoji-reaction path.",
    )
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.block_kit:
        ts = notify_decision_block_kit(args.message, args.event_id, channel=args.recipient)
    else:
        ts = notify_decision(args.message, args.event_id, slack_user=args.recipient)
    print(f"ts={ts}")
