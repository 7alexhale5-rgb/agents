"""PF_EPISODIC env selection for episodic client."""
from __future__ import annotations

import pytest

from pf_runtime.memory.tier3_episodic import (
    LaikEpisodicStub,
    NoOpEpisodicClient,
    episodic_client_from_env,
)


def test_episodic_default_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PF_EPISODIC", raising=False)
    c = episodic_client_from_env()
    assert isinstance(c, NoOpEpisodicClient)


@pytest.mark.parametrize(
    "raw",
    ["noop", "NOOP", " Noop "],
)
def test_episodic_explicit_noop(
    monkeypatch: pytest.MonkeyPatch,
    raw: str,
) -> None:
    monkeypatch.setenv("PF_EPISODIC", raw)
    assert isinstance(episodic_client_from_env(), NoOpEpisodicClient)


def test_episodic_laik_stub(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PF_EPISODIC", "laik")
    assert isinstance(episodic_client_from_env(), LaikEpisodicStub)


@pytest.mark.asyncio
async def test_noop_query_write_roundtrip() -> None:
    c = NoOpEpisodicClient()
    assert await c.query("q", "p") == []
    await c.write("memo", "p")
