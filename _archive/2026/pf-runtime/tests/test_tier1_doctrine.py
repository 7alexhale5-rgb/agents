from __future__ import annotations

from pathlib import Path

from pf_runtime.config import Profile
from pf_runtime.memory.tier1_soul import SoulReader


def test_soul_reader_includes_optional_doctrine(tmp_path: Path) -> None:
    profile = _profile(tmp_path)
    (tmp_path / "DOCTRINE.md").write_text("constraint first", encoding="utf-8")

    text = SoulReader().read(profile)

    assert "=== SOUL.md ===" in text
    assert "=== DOCTRINE.md ===" in text
    assert "constraint first" in text
    assert text.index("=== SOUL.md ===") < text.index("=== DOCTRINE.md ===")
    assert text.index("=== DOCTRINE.md ===") < text.index("=== USER.md ===")


def test_soul_reader_omits_missing_doctrine(tmp_path: Path) -> None:
    profile = _profile(tmp_path)

    text = SoulReader().read(profile)

    assert "=== DOCTRINE.md ===" not in text


def _profile(tmp_path: Path) -> Profile:
    (tmp_path / "SOUL.md").write_text("soul", encoding="utf-8")
    (tmp_path / "USER.md").write_text("user", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text("", encoding="utf-8")
    (tmp_path / ".env").write_text("K=v\n", encoding="utf-8")
    return Profile(
        slug="atlas-ceo",
        model="x/y",
        provider="openrouter",
        soul_md_path=tmp_path / "SOUL.md",
        user_md_path=tmp_path / "USER.md",
        memory_md_path=tmp_path / "MEMORY.md",
        env_path=tmp_path / ".env",
    )
