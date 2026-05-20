"""Tier 3 memory — Episodic / vector-store client stub.

Ships as a no-op in sub-phase B. LAIK MCP integration lands in sub-phase D.

ABC contract:
    query(query: str, profile_slug: str) -> list[str]
    write(content: str, profile_slug: str) -> None
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


class EpisodicClient(ABC):
    """Abstract interface for the Tier 3 episodic memory store."""

    @abstractmethod
    async def query(self, query: str, profile_slug: str) -> list[str]:
        """Return top-k relevant passages from episodic memory.

        Args:
            query: Natural-language query string.
            profile_slug: Profile whose episodic store to search.

        Returns:
            List of relevant text passages (most relevant first).

        Raises:
            NotImplementedError: in concrete stubs that haven't wired LAIK yet.
        """
        raise NotImplementedError

    @abstractmethod
    async def write(self, content: str, profile_slug: str) -> None:
        """Persist *content* into the episodic store for *profile_slug*.

        Args:
            content: Text to embed and store.
            profile_slug: Profile whose episodic store to write.

        Raises:
            NotImplementedError: in concrete stubs that haven't wired LAIK yet.
        """
        raise NotImplementedError


class NoOpEpisodicClient(EpisodicClient):
    """Satisfies the EpisodicClient ABC; used until LAIK MCP is fully wired."""

    async def query(self, query: str, profile_slug: str) -> list[str]:
        del query, profile_slug
        return []

    async def write(self, content: str, profile_slug: str) -> None:
        del content, profile_slug
        return


class LaikEpisodicStub(EpisodicClient):
    """Feature-flag hook for LAIK MCP (`PF_EPISODIC=laik`). Returns empty until wired."""

    async def query(self, query: str, profile_slug: str) -> list[str]:
        del query, profile_slug
        return []

    async def write(self, content: str, profile_slug: str) -> None:
        del content, profile_slug
        return


def episodic_client_from_env() -> EpisodicClient:
    """Select episodic backend via ``PF_EPISODIC`` (``noop`` | ``laik``)."""
    mode = os.environ.get("PF_EPISODIC", "noop").strip().lower()
    if mode == "laik":
        return LaikEpisodicStub()
    return NoOpEpisodicClient()
