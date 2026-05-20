from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from pf_runtime.runtime import model_adapter as model_adapter_module
from pf_runtime.runtime.model_adapter import (
    ModelAdapter,
    RoutingModelAdapter,
    _to_openrouter_messages,
)


class _FakeAdapter(ModelAdapter):
    def __init__(self, env_path: Path, *, replies: list[tuple[str, Decimal]] | None = None) -> None:
        del env_path
        self.replies = replies or []
        self.calls: list[str] = []

    async def complete(
        self,
        messages: list[dict[str, object]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del messages, max_tokens
        self.calls.append(model)
        if self.replies:
            return self.replies.pop(0)
        return "ok", Decimal("0")


class _FailingAdapter(_FakeAdapter):
    async def complete(
        self,
        messages: list[dict[str, object]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        del messages, max_tokens
        self.calls.append(model)
        raise RuntimeError("provider unavailable")


@pytest.mark.asyncio
async def test_routing_model_adapter_uses_direct_anthropic_when_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anthropic = _FakeAdapter(tmp_path, replies=[("premium direct", Decimal("0.01"))])
    openrouter = _FakeAdapter(tmp_path)
    monkeypatch.setattr(model_adapter_module, "AnthropicMessagesAdapter", lambda env_path: anthropic)
    monkeypatch.setattr(model_adapter_module, "OpenRouterAdapter", lambda env_path: openrouter)
    adapter = RoutingModelAdapter(tmp_path / ".env", fallback_model="nvidia/free")

    content, cost = await async_complete(adapter, "anthropic:claude-sonnet-4-6")

    assert content == "premium direct"
    assert cost == Decimal("0.01")
    assert anthropic.calls == ["claude-sonnet-4-6"]
    assert openrouter.calls == []


@pytest.mark.asyncio
async def test_routing_model_adapter_uses_premium_openrouter_mirror_on_anthropic_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    anthropic = _FailingAdapter(tmp_path)
    openrouter = _FakeAdapter(tmp_path, replies=[("premium mirror", Decimal("0.02"))])
    monkeypatch.setattr(model_adapter_module, "AnthropicMessagesAdapter", lambda env_path: anthropic)
    monkeypatch.setattr(model_adapter_module, "OpenRouterAdapter", lambda env_path: openrouter)
    adapter = RoutingModelAdapter(tmp_path / ".env", fallback_model="nvidia/free")

    content, cost = await async_complete(adapter, "anthropic:claude-sonnet-4-6")

    assert content == "premium mirror"
    assert cost == Decimal("0.02")
    assert anthropic.calls == ["claude-sonnet-4-6"]
    assert openrouter.calls == ["anthropic/claude-sonnet-4.6"]


@pytest.mark.asyncio
async def test_routing_model_adapter_marks_degraded_only_when_premium_paths_fail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _OpenRouterWithFallback(_FakeAdapter):
        async def complete(
            self,
            messages: list[dict[str, object]],
            *,
            model: str,
            max_tokens: int = 1024,
        ) -> tuple[str, Decimal]:
            del messages, max_tokens
            self.calls.append(model)
            if model.startswith("anthropic/"):
                raise RuntimeError("mirror unavailable")
            return "fallback answer", Decimal("0")

    anthropic = _FailingAdapter(tmp_path)
    openrouter = _OpenRouterWithFallback(tmp_path)
    monkeypatch.setattr(model_adapter_module, "AnthropicMessagesAdapter", lambda env_path: anthropic)
    monkeypatch.setattr(model_adapter_module, "OpenRouterAdapter", lambda env_path: openrouter)
    adapter = RoutingModelAdapter(tmp_path / ".env", fallback_model="nvidia/free")

    content, cost = await async_complete(adapter, "anthropic:claude-sonnet-4-6")

    assert "[DEGRADED_MODEL_ROUTE" in content
    assert "fallback answer" in content
    assert cost == Decimal("0")
    assert openrouter.calls == ["anthropic/claude-sonnet-4.6", "nvidia/free"]


def test_openrouter_anthropic_messages_convert_tool_results_to_user_messages() -> None:
    messages = [
        {"role": "system", "content": "rules"},
        {"role": "assistant", "content": "calling tool"},
        {"role": "tool", "content": "{\"ok\": true}"},
    ]

    converted = _to_openrouter_messages("anthropic/claude-sonnet-4.6", messages)

    assert converted == [
        {"role": "system", "content": "rules"},
        {"role": "assistant", "content": "calling tool"},
        {"role": "user", "content": "Tool result:\n{\"ok\": true}"},
    ]


async def async_complete(adapter: RoutingModelAdapter, model: str) -> tuple[str, Decimal]:
    return await adapter.complete([{"role": "user", "content": "hi"}], model=model)
