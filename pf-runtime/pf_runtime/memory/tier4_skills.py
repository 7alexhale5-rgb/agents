"""Tier 4 memory — per-profile SkillRegistry.

Sub-phase D: ``ProfileSkillRegistry`` reads ONLY ``{hermes_home}/profiles/{slug}/skills/**/*.md``.

Tier 4 isolation hard contract (MEMORY_LIFECYCLE.md + THREAT_MODEL.md §A4):
    - SkillRegistry MUST refuse profile_slug=None or empty string with ValueError
      at every method boundary — including on the no-op stub.
    - Reads ONLY from hermes/profiles/{slug}/skills/ — never from shared
      ~/.hermes/skills/ (that path is Phase 5 marketplace, exempt from this registry).

ABC contract:
    list_skills(profile_slug: str) -> list[str]
    load_skill(slug: str, profile_slug: str) -> str
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


def _require_slug(profile_slug: str) -> None:
    """Raise ValueError when profile_slug is None-ish or empty.

    This is the Tier 4 isolation contract enforcement point. Every method
    that touches per-profile data MUST call this before doing anything else.
    """
    if not profile_slug:
        raise ValueError(
            "profile_slug must be a non-empty string (Tier 4 isolation contract). "
            "SkillRegistry must refuse empty or None slugs to prevent cross-profile leaks."
        )


class SkillRegistry(ABC):
    """Abstract interface for the Tier 4 per-profile skill registry."""

    @abstractmethod
    def list_skills(self, profile_slug: str) -> list[str]:
        """Return skill slugs available for *profile_slug*.

        Args:
            profile_slug: Non-empty profile identifier.

        Returns:
            List of skill slugs.

        Raises:
            ValueError: if profile_slug is empty or None.
            NotImplementedError: in stubs.
        """
        raise NotImplementedError

    @abstractmethod
    def load_skill(self, slug: str, profile_slug: str) -> str:
        """Return the body of the skill identified by *slug* for *profile_slug*.

        Args:
            slug: Skill identifier.
            profile_slug: Non-empty profile identifier.

        Returns:
            Skill body text.

        Raises:
            ValueError: if profile_slug is empty or None (Tier 4 contract).
            KeyError: if the skill does not exist for this profile.
            NotImplementedError: in stubs.
        """
        raise NotImplementedError


class NoOpSkillRegistry(SkillRegistry):
    """Satisfies the SkillRegistry ABC; used in tests that must not touch disk.

    Tier 4 isolation enforcement is still active on this stub — the slug
    guard fires on every method even though the registry is empty.
    """

    def list_skills(self, profile_slug: str) -> list[str]:
        """Returns an empty list. Raises ValueError for empty/None profile_slug."""
        _require_slug(profile_slug)
        return []

    def load_skill(self, slug: str, profile_slug: str) -> str:
        """Raises ValueError for empty/None profile_slug; KeyError for any slug."""
        _require_slug(profile_slug)
        raise KeyError(
            f"Skill '{slug}' not found for profile '{profile_slug}' "
            "(NoOpSkillRegistry has no skills — sub-phase D wires real skills)"
        )


class ProfileSkillRegistry(SkillRegistry):
    """Load markdown skills from ``HERMES_HOME/profiles/<slug>/skills/`` only.

    Skill *slug* is the path relative to ``skills/`` without the ``.md`` suffix
    (POSIX ``/`` segments), e.g. ``nested/foo`` for ``skills/nested/foo.md``.
    """

    def __init__(self, hermes_home: Path) -> None:
        self._hermes_home = hermes_home.expanduser().resolve()

    def _skills_dir(self, profile_slug: str) -> Path:
        _require_slug(profile_slug)
        return (self._hermes_home / "profiles" / profile_slug / "skills").resolve()

    def list_skills(self, profile_slug: str) -> list[str]:
        _require_slug(profile_slug)
        root = self._skills_dir(profile_slug)
        if not root.is_dir():
            return []
        out: list[str] = []
        root_resolved = root.resolve()
        for path in sorted(root_resolved.rglob("*.md")):
            resolved = path.resolve()
            try:
                rel = resolved.relative_to(root_resolved)
            except ValueError:
                continue
            out.append(rel.with_suffix("").as_posix())
        return out

    def load_skill(self, slug: str, profile_slug: str) -> str:
        _require_slug(profile_slug)
        if not slug or slug.strip() != slug:
            raise KeyError(f"invalid skill slug: {slug!r}")
        if ".." in Path(slug).parts:
            raise KeyError(f"invalid skill slug (path traversal): {slug!r}")
        segments = slug.split("/")
        if any(s == "" for s in segments):
            raise KeyError(f"invalid skill slug: {slug!r}")

        root = self._skills_dir(profile_slug)
        root_resolved = root.resolve()
        if not root_resolved.is_dir():
            raise KeyError(
                f"no skills directory for profile {profile_slug!r}: {root_resolved}"
            )

        # slug may use POSIX slashes; map to OS path under root
        relative = Path(*segments)
        candidate = (root_resolved / relative).with_suffix(".md").resolve()
        try:
            candidate.relative_to(root_resolved)
        except ValueError as e:
            raise KeyError(
                f"Skill {slug!r} not found for profile {profile_slug!r}"
            ) from e
        if not candidate.is_file():
            raise KeyError(
                f"Skill {slug!r} not found for profile {profile_slug!r}"
            )
        return candidate.read_text(encoding="utf-8")


def default_skill_registry(hermes_home: Path | None = None) -> SkillRegistry:
    """Return the production Tier 4 registry for ``hermes_home`` (default ``~/.hermes``)."""
    home = (
        hermes_home.expanduser().resolve()
        if hermes_home is not None
        else (Path.home() / ".hermes").resolve()
    )
    return ProfileSkillRegistry(home)
