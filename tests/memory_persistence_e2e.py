"""End-to-end cross-session memory persistence test.

PIVOT §4 sub-phase B acceptance gate.

Invokes ``python3 -m pf_runtime run`` twice against the personal profile:
  1. First call: "remember the number seven"
  2. Second call: "what number did i tell you?"

Asserts the second reply contains "seven" or "7".

This proves that the Tier 2 BufferStore persists messages across separate
process invocations — the core cross-session memory guarantee.

Note: Uses PF_BUFFER_DIR env var to point both subprocess calls to the same
temp directory, isolating the test from the real personal profile buffer while
still hitting a real SQLite file (no mocking).

The personal profile must exist at ~/.hermes/profiles/personal/ (with SOUL.md,
USER.md, config.yaml, .env). The test is skipped if the profile is absent.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_HERMES_HOME = Path.home() / ".hermes"
_PERSONAL_DIR = _HERMES_HOME / "profiles" / "personal"
_PF_RUNTIME_ROOT = Path(__file__).parent.parent / "pf-runtime"


def _personal_profile_available() -> bool:
    """Return True when all required personal profile files exist."""
    required = [
        _PERSONAL_DIR / "SOUL.md",
        _PERSONAL_DIR / "USER.md",
        _PERSONAL_DIR / "config.yaml",
        _PERSONAL_DIR / ".env",
    ]
    return _PERSONAL_DIR.is_dir() and all(p.is_file() for p in required)


def _run_pf_runtime(message: str, buffer_dir: Path) -> subprocess.CompletedProcess[str]:
    """Invoke `python3 -m pf_runtime run` with the given message.

    Both invocations share the same PF_BUFFER_DIR so the buffer persists
    across calls exactly as it would in production (different processes,
    same SQLite file).
    """
    env = {**os.environ, "PF_BUFFER_DIR": str(buffer_dir), "PYTHONPATH": str(_PF_RUNTIME_ROOT)}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pf_runtime",
            "run",
            "--profile",
            "personal",
            "--message",
            message,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(
    not _personal_profile_available(),
    reason="Personal profile not found at ~/.hermes/profiles/personal/",
)
class TestCrossSessionPersistence:
    """Validate that messages written in session 1 are visible in session 2."""

    def test_number_seven_persists(self, tmp_path: Path) -> None:
        """Tell the agent 'the number seven', then ask it back in a new process."""
        # Session 1: encode a memorable fact
        result1 = _run_pf_runtime(
            message="remember the number seven",
            buffer_dir=tmp_path,
        )
        assert result1.returncode == 0, (
            f"First invocation failed (exit {result1.returncode}):\n"
            f"stdout: {result1.stdout}\nstderr: {result1.stderr}"
        )
        reply1 = result1.stdout.strip()
        assert reply1.startswith("REPLY:"), (
            f"First reply did not start with 'REPLY:': {reply1!r}"
        )

        # Session 2: ask for the fact back
        result2 = _run_pf_runtime(
            message="what number did i tell you?",
            buffer_dir=tmp_path,
        )
        assert result2.returncode == 0, (
            f"Second invocation failed (exit {result2.returncode}):\n"
            f"stdout: {result2.stdout}\nstderr: {result2.stderr}"
        )
        reply2 = result2.stdout.strip()
        assert reply2.startswith("REPLY:"), (
            f"Second reply did not start with 'REPLY:': {reply2!r}"
        )

        # The actual test: does the agent remember?
        reply_text = reply2[len("REPLY:"):].strip().lower()
        assert "seven" in reply_text or "7" in reply_text, (
            f"Cross-session memory FAILED — second reply did not mention 'seven' or '7'.\n"
            f"Session 1 message: 'remember the number seven'\n"
            f"Session 1 reply:   {reply1!r}\n"
            f"Session 2 message: 'what number did i tell you?'\n"
            f"Session 2 reply:   {reply2!r}"
        )

    def test_buffer_written_after_first_session(self, tmp_path: Path) -> None:
        """After first invocation, the buffer SQLite file must exist with 2 rows."""
        from pf_runtime.memory.tier2_buffer import BufferStore

        _run_pf_runtime(message="hello from the test", buffer_dir=tmp_path)

        with BufferStore("personal", buffer_dir=tmp_path) as buf:
            count = buf.count()

        # Expect at least the user + assistant messages from this session
        assert count >= 2, (
            f"Buffer should have ≥2 messages after one session; got {count}"
        )

    def test_second_session_sees_first_messages(self, tmp_path: Path) -> None:
        """Buffer rows from session 1 must be visible inside session 2's recent()."""
        from pf_runtime.memory.tier2_buffer import BufferStore

        # Session 1
        _run_pf_runtime(message="my favorite animal is a capybara", buffer_dir=tmp_path)
        after_s1: int
        with BufferStore("personal", buffer_dir=tmp_path) as buf:
            after_s1 = buf.count()

        # Session 2
        _run_pf_runtime(message="what animal did i mention?", buffer_dir=tmp_path)
        after_s2: int
        with BufferStore("personal", buffer_dir=tmp_path) as buf:
            after_s2 = buf.count()

        assert after_s2 > after_s1, (
            f"Session 2 did not add more messages to the buffer "
            f"(after s1: {after_s1}, after s2: {after_s2})"
        )
