"""Memory stack composer — assembles all four tiers into a single interface.

Sub-phase B ships Tier 1 (SoulReader) and Tier 2 (BufferStore) fully wired.
Sub-phase D wires ``ProfileSkillRegistry`` via ``default_skill_registry(hermes_home)``.
Tier 3 (EpisodicClient) remains a no-op stub until later in sub-phase D.

Usage::

    from pf_runtime.memory import MemoryStack
    from pf_runtime.memory.tier1_soul import SoulReader
    from pf_runtime.memory.tier2_buffer import BufferStore
    from pf_runtime.memory.tier3_episodic import NoOpEpisodicClient
    from pf_runtime.memory.tier4_skills import default_skill_registry

    memory = MemoryStack(
        soul=SoulReader(),
        buffer=BufferStore(profile.slug),
        episodic=NoOpEpisodicClient(),
        skills=default_skill_registry(Path.home() / ".hermes"),
    )
"""
from __future__ import annotations

from dataclasses import dataclass

from pf_runtime.config import Message, Profile
from pf_runtime.memory.tier1_soul import SoulReader
from pf_runtime.memory.tier2_buffer import BufferStore
from pf_runtime.memory.tier3_episodic import EpisodicClient
from pf_runtime.memory.tier4_skills import SkillRegistry


@dataclass
class MemoryStack:
    """Composer for all four memory tiers.

    Tier 1-2 are required. Tier 3 (episodic) defaults to a NoOp until wired.
    Tier 4 (``skills``) should use ``default_skill_registry(hermes_home)`` in
    gateway/CLI; tests may pass ``NoOpSkillRegistry``.
    """

    soul: SoulReader
    buffer: BufferStore
    episodic: EpisodicClient | None = None
    skills: SkillRegistry | None = None

    def system_prompt(self, profile: Profile) -> str:
        """Return the Tier 1 context block for *profile*.

        Reads SOUL.md + USER.md + MEMORY.md (mtime-cached, 30s TTL).
        The returned string is prepended to the LLM system prompt so the
        agent has full persona + operator context every turn.
        """
        return self.soul.read(profile)

    def recent_messages(self, profile: Profile, limit: int = 10) -> list[Message]:
        """Return the last *limit* messages from the Tier 2 buffer.

        Messages are returned most-recent first (timestamp DESC) so the
        caller can reverse them if needed for chronological display.

        Args:
            profile: Profile whose buffer to query.
            limit: Maximum number of messages to return.

        Returns:
            List of Message objects (most recent first).
        """
        return self.buffer.recent(limit=limit)

    def append(self, profile: Profile, message: Message) -> None:
        """Persist *message* into the Tier 2 buffer for *profile*.

        Args:
            profile: Profile whose buffer to write.
            message: The message to persist.
        """
        self.buffer.append(message)
