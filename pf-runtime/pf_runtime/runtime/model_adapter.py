"""Model adapters — thin HTTP wrappers around LLM provider APIs.

Sub-phase A (throwaway) ships OpenRouterAdapter only:
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
_FREE_SLUG_RE = re.compile(r":free$")


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
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8"))  # type: ignore[no-any-return]

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
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }

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
