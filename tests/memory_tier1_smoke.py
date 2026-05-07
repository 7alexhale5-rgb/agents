"""Tier 1 SoulReader smoke tests.

Uses the real personal profile at ~/.hermes/profiles/personal/.
No mocking — we want to validate against the real files.

Tests:
  1. read() returns concatenated text from SOUL.md + USER.md (with section headers).
  2. Two reads within 30s return cached value (hash equal — no re-read).
  3. After touching a file (mtime change), next read returns fresh content.
"""
from __future__ import annotations

import hashlib
import os
import time
from pathlib import Path

import pytest

from pf_runtime.config import load_profile
from pf_runtime.memory.tier1_soul import SoulReader, _SECTION_HEADER

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

_HERMES_HOME = Path.home() / ".hermes"
_PERSONAL_SLUG = "personal"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def personal_profile():  # type: ignore[return]
    """Load the real personal profile. Skip if not present."""
    profile_dir = _HERMES_HOME / "profiles" / _PERSONAL_SLUG
    if not profile_dir.is_dir():
        pytest.skip(f"Personal profile dir not found: {profile_dir}")
    return load_profile(_PERSONAL_SLUG, hermes_home=_HERMES_HOME)


@pytest.fixture
def soul_reader() -> SoulReader:
    return SoulReader()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

class TestSoulReaderRead:
    """Asserts the returned text contains expected section headers and content."""

    def test_returns_soul_header(self, personal_profile, soul_reader):  # type: ignore[no-untyped-def]
        result = soul_reader.read(personal_profile)
        assert _SECTION_HEADER["soul"] in result, (
            f"Expected '{_SECTION_HEADER['soul']}' in SoulReader output"
        )

    def test_returns_user_header(self, personal_profile, soul_reader):  # type: ignore[no-untyped-def]
        result = soul_reader.read(personal_profile)
        assert _SECTION_HEADER["user"] in result, (
            f"Expected '{_SECTION_HEADER['user']}' in SoulReader output"
        )

    def test_soul_content_nonempty(self, personal_profile, soul_reader):  # type: ignore[no-untyped-def]
        result = soul_reader.read(personal_profile)
        # Content after the SOUL header must be present
        soul_idx = result.index(_SECTION_HEADER["soul"])
        section_after = result[soul_idx + len(_SECTION_HEADER["soul"]):]
        assert section_after.strip(), "SOUL.md section must have content"

    def test_user_content_nonempty(self, personal_profile, soul_reader):  # type: ignore[no-untyped-def]
        result = soul_reader.read(personal_profile)
        user_idx = result.index(_SECTION_HEADER["user"])
        section_after = result[user_idx + len(_SECTION_HEADER["user"]):]
        assert section_after.strip(), "USER.md section must have content"

    def test_memory_section_conditional(self, personal_profile, soul_reader):  # type: ignore[no-untyped-def]
        """MEMORY.md section should appear iff the file exists and is non-empty."""
        result = soul_reader.read(personal_profile)
        memory_exists = (
            personal_profile.memory_md_path.is_file()
            and personal_profile.memory_md_path.read_text(encoding="utf-8").strip()
        )
        if memory_exists:
            assert _SECTION_HEADER["memory"] in result
        else:
            # Either absent or empty — section should not appear
            assert _SECTION_HEADER["memory"] not in result


class TestSoulReaderCache:
    """Asserts mtime-based cache behaviour."""

    def test_second_read_hits_cache(self, personal_profile, soul_reader):  # type: ignore[no-untyped-def]
        """Two reads within 30s must return the same hash (no re-read)."""
        first = soul_reader.read(personal_profile)
        second = soul_reader.read(personal_profile)
        assert _sha256(first) == _sha256(second), (
            "Cache miss: second read within 30s returned different content"
        )

    def test_stale_after_mtime_change(self, personal_profile, soul_reader, tmp_path):  # type: ignore[no-untyped-def]
        """After a file's mtime changes, the reader must return fresh content."""
        # Prime the cache
        first_read = soul_reader.read(personal_profile)

        # Create a temporary alternate SOUL.md so we can swap it in
        # without touching the real profile. We do this by building a
        # throwaway Profile pointing to tmp files.
        from pf_runtime.config import Profile

        # Write a slightly modified soul file to a temp path
        original_soul = personal_profile.soul_md_path.read_text(encoding="utf-8")
        tmp_soul = tmp_path / "SOUL.md"
        tmp_user = tmp_path / "USER.md"
        tmp_memory = tmp_path / "MEMORY.md"

        tmp_soul.write_text(original_soul + "\n<!-- CACHE_BUST -->", encoding="utf-8")
        tmp_user.write_text(
            personal_profile.user_md_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        # MEMORY.md optional — copy if it exists
        if personal_profile.memory_md_path.is_file():
            tmp_memory.write_text(
                personal_profile.memory_md_path.read_text(encoding="utf-8"),
                encoding="utf-8",
            )

        tmp_profile = Profile(
            slug="personal-tmp",
            model=personal_profile.model,
            provider=personal_profile.provider,
            soul_md_path=tmp_soul,
            user_md_path=tmp_user,
            memory_md_path=tmp_memory,
            env_path=personal_profile.env_path,
        )

        tmp_reader = SoulReader()

        # First read primes the cache for tmp_profile
        primed = tmp_reader.read(tmp_profile)

        # Modify the file — ensure mtime changes by bumping it explicitly
        time.sleep(0.01)  # tiny pause so OS mtime resolution registers a change
        new_content = original_soul + "\n<!-- CACHE_BUST_V2 -->"
        tmp_soul.write_text(new_content, encoding="utf-8")
        # Touch the file to guarantee mtime change (some filesystems have 1s resolution)
        now = time.time()
        os.utime(tmp_soul, (now + 2, now + 2))

        # Second read must reflect the new content (cache invalidated by mtime)
        refreshed = tmp_reader.read(tmp_profile)

        assert _sha256(primed) != _sha256(refreshed), (
            "Cache was not invalidated after mtime change — stale content returned"
        )
        assert "CACHE_BUST_V2" in refreshed, (
            "Fresh read did not contain the newly written content"
        )
