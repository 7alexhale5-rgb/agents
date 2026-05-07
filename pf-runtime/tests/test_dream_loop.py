"""DreamLoop writes JSONL audit lines."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from pf_runtime.dream.post_session import DreamLoop, PostSessionJob


@pytest.mark.asyncio
async def test_dream_worker_appends_jsonl(tmp_path: Path) -> None:
    home = tmp_path / "hermes"
    dl = DreamLoop(home)
    dl.start()
    job = PostSessionJob(
        profile_slug="personal",
        session_id="sid-1",
        channel="slack",
        user_preview="hi",
        assistant_preview="there",
    )
    await dl.schedule(job)
    await asyncio.sleep(0.3)
    await dl.stop()

    path = home / "profiles" / "personal" / "runtime-state" / "post_session_audit.jsonl"
    assert path.is_file()
    line = path.read_text(encoding="utf-8").strip().splitlines()[-1]
    row = json.loads(line)
    assert row["session_id"] == "sid-1"
    assert row["user_preview"] == "hi"
