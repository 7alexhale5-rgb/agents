"""Tier 4 SkillRegistry isolation — profile-local skills path only."""
from __future__ import annotations

from pathlib import Path

import pytest

from pf_runtime.memory.tier4_skills import (
    NoOpSkillRegistry,
    ProfileSkillRegistry,
    default_skill_registry,
)


def _minimal_profile_tree(hermes: Path, slug: str) -> Path:
    """Return profiles/<slug> dir (skills/ created by tests as needed)."""
    p = hermes / "profiles" / slug
    p.mkdir(parents=True)
    return p


def test_list_skills_scoped_to_profile(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    for slug, files in [
        ("personal", [("skills/hello.md", "hi")]),
        ("other", [("skills/secret.md", "nope")]),
    ]:
        base = _minimal_profile_tree(hermes, slug)
        for rel, body in files:
            path = base / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")

    reg = ProfileSkillRegistry(hermes)
    assert reg.list_skills("personal") == ["hello"]
    assert reg.list_skills("other") == ["secret"]


def test_list_skills_nested_slug(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    base = _minimal_profile_tree(hermes, "personal")
    nested = base / "skills" / "nested" / "x.md"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("body", encoding="utf-8")

    reg = ProfileSkillRegistry(hermes)
    assert reg.list_skills("personal") == ["nested/x"]


def test_load_skill_cross_profile_isolated(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    p = _minimal_profile_tree(hermes, "personal")
    (p / "skills").mkdir()
    (p / "skills" / "a.md").write_text("only-a", encoding="utf-8")
    o = _minimal_profile_tree(hermes, "other")
    (o / "skills").mkdir()
    (o / "skills" / "b.md").write_text("only-b", encoding="utf-8")

    reg = ProfileSkillRegistry(hermes)
    assert reg.load_skill("a", "personal") == "only-a"
    assert reg.load_skill("b", "other") == "only-b"
    with pytest.raises(KeyError):
        reg.load_skill("b", "personal")
    with pytest.raises(KeyError):
        reg.load_skill("a", "other")


def test_empty_profile_slug_raises(tmp_path: Path) -> None:
    reg = NoOpSkillRegistry()
    with pytest.raises(ValueError, match="Tier 4"):
        reg.list_skills("")
    reg2 = ProfileSkillRegistry(tmp_path / "hermes-unused")
    with pytest.raises(ValueError, match="Tier 4"):
        reg2.list_skills("")


def test_path_traversal_slugs_rejected(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    base = _minimal_profile_tree(hermes, "personal")
    (base / "skills").mkdir()
    (base / "skills" / "safe.md").write_text("ok", encoding="utf-8")
    reg = ProfileSkillRegistry(hermes)
    with pytest.raises(KeyError, match=r"traversal|invalid"):
        reg.load_skill("../other", "personal")
    with pytest.raises(KeyError):
        reg.load_skill("../../../etc/passwd", "personal")


def test_malformed_slug_segments(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    base = _minimal_profile_tree(hermes, "personal")
    (base / "skills").mkdir()
    (base / "skills" / "ok.md").write_text("1", encoding="utf-8")
    reg = ProfileSkillRegistry(hermes)
    with pytest.raises(KeyError, match="invalid"):
        reg.load_skill("a//b", "personal")
    with pytest.raises(KeyError, match="invalid"):
        reg.load_skill(" leading", "personal")


def test_missing_skills_dir_returns_empty_list(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    _minimal_profile_tree(hermes, "personal")
    reg = ProfileSkillRegistry(hermes)
    assert reg.list_skills("personal") == []


def test_default_skill_registry_uses_path(tmp_path: Path) -> None:
    hermes = tmp_path / "hermes"
    base = _minimal_profile_tree(hermes, "personal")
    (base / "skills").mkdir()
    (base / "skills" / "z.md").write_text("z", encoding="utf-8")
    reg = default_skill_registry(hermes)
    assert reg.list_skills("personal") == ["z"]

