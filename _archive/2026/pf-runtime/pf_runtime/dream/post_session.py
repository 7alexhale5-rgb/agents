"""Async post-session queue — audit trail MVP (no LLM compaction yet)."""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostSessionJob:
    profile_slug: str
    session_id: str
    channel: str
    user_preview: str
    assistant_preview: str


class DreamLoop:
    """Bounded queue of completed sessions; worker appends JSONL audit lines."""

    def __init__(self, hermes_home: Path, *, max_queue: int = 256) -> None:
        self._hermes_home = hermes_home.expanduser().resolve()
        self._queue: asyncio.Queue[PostSessionJob] = asyncio.Queue(maxsize=max_queue)
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped.clear()
            self._task = asyncio.create_task(self._worker(), name="dream-loop-worker")

    async def stop(self) -> None:
        self._stopped.set()
        if self._task and not self._task.done():
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        self._task = None

    async def schedule(self, job: PostSessionJob) -> None:
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            _log.warning("DreamLoop queue full; dropping session %s", job.session_id)

    def _audit_path(self, profile_slug: str) -> Path:
        p = (
            self._hermes_home
            / "profiles"
            / profile_slug
            / "runtime-state"
            / "post_session_audit.jsonl"
        )
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    async def _worker(self) -> None:
        while not self._stopped.is_set():
            try:
                job = await asyncio.wait_for(self._queue.get(), timeout=0.5)
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                raise
            try:
                await asyncio.to_thread(self._append_jsonl, job)
            except Exception:
                _log.exception("dream worker failed for session %s", job.session_id)
            finally:
                self._queue.task_done()

    def _append_jsonl(self, job: PostSessionJob) -> None:
        path = self._audit_path(job.profile_slug)
        payload = {
            "ts": time.time(),
            "profile_slug": job.profile_slug,
            "session_id": job.session_id,
            "channel": job.channel,
            "user_preview": job.user_preview[:500],
            "assistant_preview": job.assistant_preview[:500],
        }
        line = json.dumps(payload, ensure_ascii=False) + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
