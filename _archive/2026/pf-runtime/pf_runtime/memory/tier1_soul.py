"""Tier 1 memory — SOUL.md / DOCTRINE.md / USER.md / MEMORY.md reader.

Read-only at runtime. Cache TTL is 30s; invalidated when ANY tracked
file mtimes change (or when the set of existing files changes).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from pf_runtime.config import Profile

_CACHE_TTL_SECONDS = 30.0

_SECTION_HEADER = {
    "soul": "=== SOUL.md ===",
    "doctrine": "=== DOCTRINE.md ===",
    "user": "=== USER.md ===",
    "memory": "=== MEMORY.md ===",
}


@dataclass
class _CacheEntry:
    text: str
    mtimes: dict[str, float]  # path-string → mtime
    created_at: float = field(default_factory=time.monotonic)

    def is_fresh(self, current_mtimes: dict[str, float]) -> bool:
        """Return True when entry is still within TTL AND mtimes haven't changed."""
        age = time.monotonic() - self.created_at
        if age > _CACHE_TTL_SECONDS:
            return False
        return self.mtimes == current_mtimes


def _safe_mtime(path: Path) -> float:
    """Return mtime float, or 0.0 if the file doesn't exist."""
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def _read_optional(path: Path) -> str:
    """Read a file; return empty string if it doesn't exist."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _doctrine_path(profile: Profile) -> Path:
    return profile.soul_md_path.parent / "DOCTRINE.md"


class SoulReader:
    """Reads and caches Tier 1 context.

    One instance per runtime process; the cache is per-profile-slug so
    multiple profiles in the same process are handled correctly.
    """

    def __init__(self) -> None:
        self._cache: dict[str, _CacheEntry] = {}

    def _current_mtimes(self, profile: Profile) -> dict[str, float]:
        return {
            str(profile.soul_md_path): _safe_mtime(profile.soul_md_path),
            str(_doctrine_path(profile)): _safe_mtime(_doctrine_path(profile)),
            str(profile.user_md_path): _safe_mtime(profile.user_md_path),
            str(profile.memory_md_path): _safe_mtime(profile.memory_md_path),
        }

    def read(self, profile: Profile) -> str:
        """Return concatenated Tier 1 context for *profile*.

        Sections are only included when the file exists and is non-empty.
        Format::

            === SOUL.md ===
            <soul content>

            === DOCTRINE.md ===
            <doctrine content>

            === USER.md ===
            <user content>

            === MEMORY.md ===
            <memory content>
        """
        current_mtimes = self._current_mtimes(profile)
        cached = self._cache.get(profile.slug)
        if cached is not None and cached.is_fresh(current_mtimes):
            return cached.text

        # Cache miss or stale — re-read all three files.
        soul_text = profile.soul_md_path.read_text(encoding="utf-8").strip()
        doctrine_text = _read_optional(_doctrine_path(profile)).strip()
        user_text = profile.user_md_path.read_text(encoding="utf-8").strip()
        memory_text = _read_optional(profile.memory_md_path).strip()

        parts: list[str] = []
        if soul_text:
            parts.append(f"{_SECTION_HEADER['soul']}\n{soul_text}")
        if doctrine_text:
            parts.append(f"{_SECTION_HEADER['doctrine']}\n{doctrine_text}")
        if user_text:
            parts.append(f"{_SECTION_HEADER['user']}\n{user_text}")
        if memory_text:
            parts.append(f"{_SECTION_HEADER['memory']}\n{memory_text}")

        text = "\n\n".join(parts)
        self._cache[profile.slug] = _CacheEntry(
            text=text,
            mtimes=current_mtimes,
        )
        return text
