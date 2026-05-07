"""Tier 4 memory — Skill registry stub.

Ships as a no-op in sub-phase B. Profile-isolated SkillRegistry lands in sub-phase D.

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
    """Satisfies the SkillRegistry ABC; used until profile-local skills land (sub-phase D).

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
