"""Model adapters — thin HTTP wrappers around LLM provider APIs.

Sub-phase A (throwaway) shipped OpenRouterAdapter only:
  - Direct HTTP POST to https://openrouter.ai/api/v1/chat/completions
  - Reads OPENROUTER_API_KEY from the profile's .env via dotenv at
    adapter-init time (profile-scoped .env load avoids the gateway
    env-poisoning bug observed in Hermes v0.12.0).
  - Uses urllib.request in asyncio.to_thread (no new deps).
  - Cost estimate: always Decimal("0") for free-tier models (OR
    returns cost:0 for :free slugs).
"""
from __future__ import annotations

import abc
import asyncio
import json
import re
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path
from typing import Any

# ----- dotenv loader (stdlib only) -----

def _load_dotenv(env_path: Path) -> dict[str, str]:
    """Parse a .env file and return key→value mapping.

    Handles:
    - KEY=value
    - KEY="value"  / KEY='value'
    - # comments
    - blank lines
    Does NOT handle multi-line values or shell variable expansion.
    """
    result: dict[str, str] = {}
    if not env_path.is_file():
        return result
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, raw = line.partition("=")
        key = key.strip()
        raw = raw.strip().strip('"').strip("'")
        result[key] = raw
    return result


# ----- abstract base -----

class ModelAdapter(abc.ABC):
    @abc.abstractmethod
    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        """Send messages to the LLM and return (assistant_content, cost_usd)."""
        ...


# ----- OpenRouter adapter -----

_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
_FREE_SLUG_RE = re.compile(r":free$")


class RoutingModelAdapter(ModelAdapter):
    """Dispatch completions to the right provider from the model id."""

    def __init__(self, env_path: Path, *, fallback_model: str | None = None) -> None:
        self._env_path = env_path
        self._fallback_model = fallback_model
        self._openrouter = OpenRouterAdapter(env_path)
        self._anthropic: AnthropicMessagesAdapter | None = None

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        if model.startswith("anthropic:"):
            if self._anthropic is None:
                self._anthropic = AnthropicMessagesAdapter(self._env_path)
            anthropic_model = model.removeprefix("anthropic:")
            try:
                return await self._anthropic.complete(
                    messages,
                    model=anthropic_model,
                    max_tokens=max(max_tokens, 4096),
                )
            except Exception:
                try:
                    return await self._openrouter.complete(
                        messages,
                        model=_anthropic_openrouter_model(anthropic_model),
                        max_tokens=max(max_tokens, 4096),
                    )
                except Exception:
                    if not self._fallback_model:
                        raise
                    content, cost = await self._openrouter.complete(
                        messages,
                        model=self._fallback_model.removeprefix("openrouter:"),
                        max_tokens=max(max_tokens, 4096),
                    )
                    return (
                        "[DEGRADED_MODEL_ROUTE: premium Atlas route unavailable; "
                        "smoke-test quality only]\n"
                        f"{content}",
                        cost,
                    )
        return await self._openrouter.complete(
            messages,
            model=model.removeprefix("openrouter:"),
            max_tokens=max_tokens,
        )


class OpenRouterAdapter(ModelAdapter):
    """HTTP adapter for OpenRouter's chat completions endpoint.

    The API key is loaded from the profile's .env at construction time
    so that different profiles can use different keys, and so the adapter
    never touches os.environ directly.
    """

    def __init__(self, env_path: Path) -> None:
        env = _load_dotenv(env_path)
        api_key = env.get("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError(
                f"OPENROUTER_API_KEY not found in {env_path}. "
                "Check that the profile's .env file contains the key."
            )
        self._api_key = api_key

    def _post_sync(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Synchronous HTTP POST — runs in a thread via asyncio.to_thread."""
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _OPENROUTER_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "HTTP-Referer": "https://prettyflyforai.com",
                "X-Title": "PF-Runtime",
            },
            method="POST",
        )
        # HTTPS fixed host _OPENROUTER_URL only; POST body built from adapter (no user URL).
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:  # nosec B310
                return _read_json_response(resp, label="OpenRouter")
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter API error {exc.code}: {body_text}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter API transport error: {exc.reason}") from exc

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        """Send a chat completion request to OpenRouter.

        Returns:
            (assistant_content, cost_usd_estimate)

        Cost estimate is Decimal("0") for free-tier model slugs (:free
        suffix) since OpenRouter returns cost=0 for those. For paid
        models, OR returns usage.cost in the response and we pass it
        through; this throwaway version always returns 0 since the
        personal profile uses the :free model.
        """
        payload: dict[str, Any] = {
            "model": model,
            "messages": _to_openrouter_messages(model, messages),
            "max_tokens": max_tokens,
        }
        if not model.startswith("anthropic/claude-"):
            payload["temperature"] = 0.7

        response = await asyncio.to_thread(self._post_sync, payload)

        # Extract assistant content
        choices = response.get("choices", [])
        if not choices:
            raise RuntimeError(
                f"OpenRouter returned no choices. Full response: {response}"
            )
        content = choices[0].get("message", {}).get("content", "")
        if not isinstance(content, str):
            raise RuntimeError(
                f"Unexpected content type from OpenRouter: {type(content)!r}"
            )

        # Cost — OR returns usage.cost for paid models; 0 for :free slugs
        cost_raw = response.get("usage", {}).get("cost", 0)
        cost_usd = Decimal(str(cost_raw)) if cost_raw else Decimal("0")

        return content, cost_usd


class AnthropicMessagesAdapter(ModelAdapter):
    """Minimal direct Anthropic Messages API adapter for Atlas brief routing."""

    def __init__(self, env_path: Path) -> None:
        env = _load_dotenv(env_path)
        api_key = env.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError(
                f"ANTHROPIC_API_KEY not found in {env_path}. "
                "Check that the profile's .env file contains the key."
            )
        self._api_key = api_key

    def _post_sync(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            _ANTHROPIC_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:  # nosec B310
                return _read_json_response(resp, label="Anthropic")
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {body_text}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Anthropic API transport error: {exc.reason}") from exc

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        system, anthropic_messages = _to_anthropic_messages(messages)
        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": max_tokens,
        }
        if system:
            payload["system"] = system

        response = await asyncio.to_thread(self._post_sync, payload)
        content_parts = response.get("content", [])
        text_parts = [
            part.get("text", "")
            for part in content_parts
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        content = "\n".join(part for part in text_parts if part)
        if not content:
            raise RuntimeError(f"Anthropic returned no text content: {response}")
        return content, Decimal("0")


def _to_anthropic_messages(
    messages: list[dict[str, Any]],
) -> tuple[str, list[dict[str, str]]]:
    system_parts: list[str] = []
    converted: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
        if role == "system":
            system_parts.append(content)
        elif role == "assistant":
            converted.append({"role": "assistant", "content": content})
        elif role == "tool":
            converted.append({"role": "user", "content": f"Tool result:\n{content}"})
        else:
            converted.append({"role": "user", "content": content})

    if not converted:
        converted.append({"role": "user", "content": ""})
    return "\n\n".join(system_parts), converted


def _to_openrouter_messages(
    model: str,
    messages: list[dict[str, Any]],
) -> list[dict[str, str]]:
    if not model.startswith("anthropic/claude-"):
        return [
            {
                "role": str(message.get("role", "user")),
                "content": str(message.get("content", "")),
            }
            for message in messages
        ]

    converted: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role", "user"))
        content = str(message.get("content", ""))
        if role in {"system", "assistant", "user"}:
            converted.append({"role": role, "content": content})
        elif role == "tool":
            converted.append({"role": "user", "content": f"Tool result:\n{content}"})
        else:
            converted.append({"role": "user", "content": content})
    return converted


def _anthropic_openrouter_model(model: str) -> str:
    normalized = model.replace("-4-7", "-4.7").replace("-4-6", "-4.6")
    return f"anthropic/{normalized}"


def _read_json_response(resp: Any, *, label: str) -> dict[str, Any]:
    content_type = str(resp.headers.get("Content-Type", ""))
    body = resp.read().decode("utf-8", errors="replace")
    if "json" not in content_type.lower():
        raise RuntimeError(f"{label} returned non-json content: {content_type or 'unknown'}")
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} returned invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise RuntimeError(f"{label} returned {type(data).__name__}, expected object")
    return data
