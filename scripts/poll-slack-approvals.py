#!/usr/bin/env python3
"""Poll Slack for emoji reactions on fleet decision DMs, update agent_events.status.

Runs on a cron every 5 min. For each tracked Slack message (those posted by
hermes/lib/slack_notify.py — identified by the "_event:<uuid>_" footer
they include), polls reactions, maps emoji → status, updates the matching
agent_events row via direct service-role Supabase write.

Approval mapping (mirrors slack_notify.APPROVAL_FOOTER):
  ✅ → status='approved'
  ✏️ → status='revise'
  ❌ → status='rejected'

Idempotency: only updates rows where current status='pending'. A second
reaction (Alex changing his mind) is logged + flagged but does NOT
overwrite a non-pending row. Manual SQL is the only way to override
once a status is set.

State tracking: ~/.config/prettyfly-marketing/slack-poll-state.json holds
the last-processed timestamp per channel so the poller doesn't re-process
old messages.

Requires:
- SLACK_BOT_TOKEN (with reactions:read, channels:history, im:history scopes)
- SUPABASE_DB_URL or `supabase db query --linked` configured

Usage:
  python3 scripts/poll-slack-approvals.py            # poll once + exit
  python3 scripts/poll-slack-approvals.py --once     # explicit one-shot
  python3 scripts/poll-slack-approvals.py --dry-run  # log what would change, don't write
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import urllib.request
import urllib.error
import urllib.parse

logger = logging.getLogger(__name__)

EMOJI_TO_STATUS = {
    "white_check_mark": "approved",
    "heavy_check_mark": "approved",
    "memo": "revise",
    "pencil2": "revise",
    "x": "rejected",
    "no_entry_sign": "rejected",
}

EVENT_ID_RE = re.compile(r"_event:([0-9a-f-]{36})_")

STATE_FILE = Path.home() / ".config" / "prettyfly-marketing" / "slack-poll-state.json"


def slack_api(method: str, params: dict, token: str) -> dict:
    """Call Slack Web API. Returns parsed JSON."""
    url = f"https://slack.com/api/{method}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.error("Slack API %s failed: HTTP %d", method, exc.code)
        return {"ok": False, "error": f"http_{exc.code}"}
    except Exception as exc:  # noqa: BLE001
        logger.error("Slack API %s failed: %s", method, exc)
        return {"ok": False, "error": str(exc)}


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except json.JSONDecodeError:
            logger.warning("State file corrupt, resetting")
    return {"channels": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def update_agent_event_status(event_id: str, new_status: str, dry_run: bool = False) -> bool:
    """Update agent_events.status via service-role Supabase query.

    Only writes if current status='pending' (idempotency guard).
    Returns True on successful update, False on any failure or skip.
    """
    sql = (
        f"UPDATE public.agent_events SET status = '{new_status}' "
        f"WHERE id = '{event_id}' AND status = 'pending' "
        f"RETURNING id, type, status;"
    )

    if dry_run:
        logger.info("DRY-RUN: would update event %s → status=%s", event_id, new_status)
        return True

    pfos_root = Path.home() / "Projects" / "prettyfly-os"
    try:
        result = subprocess.run(
            ["supabase", "db", "query", "--linked"],
            input=sql,
            capture_output=True,
            text=True,
            cwd=str(pfos_root),
            timeout=30,
        )
        if result.returncode != 0:
            logger.error("supabase update failed for %s: %s", event_id, result.stderr[:200])
            return False
        # Parse response — if rows array is non-empty, update happened
        try:
            parsed = json.loads(result.stdout)
            if parsed.get("rows"):
                logger.info("Updated event %s → status=%s", event_id, new_status)
                return True
            else:
                logger.info(
                    "Event %s NOT updated (probably already non-pending) — Slack reaction logged but not applied",
                    event_id,
                )
                return False
        except json.JSONDecodeError:
            logger.warning("Couldn't parse supabase response for %s", event_id)
            return False
    except Exception as exc:  # noqa: BLE001
        logger.error("supabase invocation failed: %s", exc)
        return False


def poll_dm_channel(channel_id: str, token: str, oldest_ts: Optional[str], dry_run: bool) -> tuple[int, Optional[str]]:
    """Poll one Slack DM channel for new messages + their reactions.

    Returns (updates_applied, latest_ts_seen).
    """
    params = {"channel": channel_id, "limit": 100}
    if oldest_ts:
        params["oldest"] = oldest_ts

    history = slack_api("conversations.history", params, token)
    if not history.get("ok"):
        logger.error("conversations.history failed for %s: %s", channel_id, history.get("error"))
        return (0, oldest_ts)

    updates = 0
    latest = oldest_ts
    for msg in history.get("messages", []):
        ts = msg.get("ts")
        if latest is None or (ts and ts > latest):
            latest = ts

        text = msg.get("text", "")
        m = EVENT_ID_RE.search(text)
        if not m:
            continue

        event_id = m.group(1)
        reactions = msg.get("reactions", [])
        for reaction in reactions:
            emoji = reaction.get("name", "")
            new_status = EMOJI_TO_STATUS.get(emoji)
            if not new_status:
                continue
            if update_agent_event_status(event_id, new_status, dry_run=dry_run):
                updates += 1
                break  # one status per message — first matching emoji wins

    return (updates, latest)


def list_dm_channels(token: str) -> list[str]:
    """Return list of DM channel IDs the bot has access to."""
    result = slack_api("conversations.list", {"types": "im", "limit": 200}, token)
    if not result.get("ok"):
        logger.error("conversations.list failed: %s", result.get("error"))
        return []
    return [c["id"] for c in result.get("channels", []) if c.get("id")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Slack reactions for fleet decision approvals.")
    parser.add_argument("--once", action="store_true", help="Poll once and exit (default; cron mode).")
    parser.add_argument("--dry-run", action="store_true", help="Log changes without writing.")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    token = os.environ.get("SLACK_BOT_TOKEN")
    if not token:
        logger.error("SLACK_BOT_TOKEN not set — cannot poll Slack")
        return 2

    state = load_state()
    total_updates = 0

    for channel_id in list_dm_channels(token):
        oldest = state["channels"].get(channel_id)
        updates, latest = poll_dm_channel(channel_id, token, oldest, dry_run=args.dry_run)
        total_updates += updates
        if latest:
            state["channels"][channel_id] = latest

    if not args.dry_run:
        save_state(state)

    logger.info("Poll complete: %d status updates applied", total_updates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
