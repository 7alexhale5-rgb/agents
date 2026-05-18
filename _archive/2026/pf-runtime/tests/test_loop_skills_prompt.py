"""Tier 4 skill previews appear in run_session system prompt."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from pf_runtime.config import InboundMessage, Profile
from pf_runtime.memory import MemoryStack
from pf_runtime.memory.tier4_skills import ProfileSkillRegistry
from pf_runtime.runtime.loop import run_session
from pf_runtime.runtime.model_adapter import ModelAdapter


def _profile(tmp_path: Path) -> Profile:
    pdir = tmp_path / "profiles" / "personal"
    pdir.mkdir(parents=True)
    (pdir / "SOUL.md").write_text("# soul", encoding="utf-8")
    (pdir / "USER.md").write_text("# user", encoding="utf-8")
    (pdir / "MEMORY.md").write_text("", encoding="utf-8")
    (pdir / ".env").write_text("K=v\n", encoding="utf-8")
    return Profile(
        slug="personal",
        model="x/y",
        provider="openrouter",
        soul_md_path=pdir / "SOUL.md",
        user_md_path=pdir / "USER.md",
        memory_md_path=pdir / "MEMORY.md",
        env_path=pdir / ".env",
    )


class _CaptureAdapter(ModelAdapter):
    def __init__(self) -> None:
        self.messages: list[dict[str, str]] | None = None

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        self.messages = messages
        return "ok", Decimal("0")


@pytest.mark.asyncio
async def test_skills_context_in_system_prompt(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    profile = _profile(hermes)
    sk = profile.soul_md_path.parent / "skills"
    sk.mkdir(parents=True, exist_ok=True)
    (sk / "hello.md").write_text(
        "# Title\nSkill body for iris.\nmore",
        encoding="utf-8",
    )

    from pf_runtime.memory.tier1_soul import SoulReader
    from pf_runtime.memory.tier2_buffer import BufferStore
    from pf_runtime.memory.tier3_episodic import NoOpEpisodicClient

    reg = ProfileSkillRegistry(hermes)
    buf = BufferStore(profile.slug)
    buf.open()
    try:
        memory = MemoryStack(
            soul=SoulReader(),
            buffer=buf,
            episodic=NoOpEpisodicClient(),
            skills=reg,
        )
        block = memory.skills_context_for_prompt(profile)
        assert "skill:hello" in block
        assert "Skill body for iris" in block

        adapter = _CaptureAdapter()
        await run_session(
            profile,
            InboundMessage(
                channel="cli",
                profile_slug="personal",
                user_id="u",
                text="ping",
            ),
            model_adapter=adapter,
            memory=memory,
        )
        assert adapter.messages is not None
        sys0 = adapter.messages[0]["content"]
        assert "skill:hello" in sys0
        assert "Skill body for iris" in sys0
    finally:
        buf.close()


def test_skills_context_empty_without_skills_dir(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    profile = _profile(hermes)
    from pf_runtime.memory.tier1_soul import SoulReader
    from pf_runtime.memory.tier2_buffer import BufferStore
    from pf_runtime.memory.tier3_episodic import NoOpEpisodicClient

    reg = ProfileSkillRegistry(hermes)
    buf = BufferStore(profile.slug)
    buf.open()
    try:
        memory = MemoryStack(
            soul=SoulReader(),
            buffer=buf,
            episodic=NoOpEpisodicClient(),
            skills=reg,
        )
        assert memory.skills_context_for_prompt(profile) == ""
    finally:
        buf.close()


@pytest.mark.asyncio
async def test_skills_budget_omits_tail(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    profile = _profile(hermes)
    sk = profile.soul_md_path.parent / "skills"
    sk.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        (sk / f"s{i}.md").write_text(f"content {i}", encoding="utf-8")

    from pf_runtime.memory.tier1_soul import SoulReader
    from pf_runtime.memory.tier2_buffer import BufferStore
    from pf_runtime.memory.tier3_episodic import NoOpEpisodicClient

    memory = MemoryStack(
        soul=SoulReader(),
        buffer=BufferStore(profile.slug),
        episodic=NoOpEpisodicClient(),
        skills=ProfileSkillRegistry(hermes),
    )
    tiny = memory.skills_context_for_prompt(profile, max_chars=200)
    assert "omitted for character budget" in tiny
