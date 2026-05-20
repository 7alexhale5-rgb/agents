"""Exa.ai REST client — direct HTTPS, stdlib-only.

Mirrors the Apollo client shape (``hermes/lib/apollo_client.py``): one tiny
wrapper per endpoint, uniform ``{results_count, query_hash, vertical, endpoint,
data}`` return envelope, stdlib urllib for the HTTP layer. No exa_py dependency.

Reads ``EXA_API_KEY`` from the environment. Hermes sources ``~/.hermes/.env``
on profile boot, so the key is available transparently to any tool call.

Two endpoints used:

  POST /search    — neural + keyword + content extraction in one call
  POST /contents  — fetch parsed content for URLs you already have

Canonical reference: https://docs.exa.ai/reference/search-api-guide-for-coding-agents
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping

API_BASE = "https://api.exa.ai"
_REQUEST_TIMEOUT_SECONDS = 30


class ExaError(RuntimeError):
    """Raised when Exa returns a non-2xx response or the API key is missing."""


def _load_api_key() -> str:
    key = (os.environ.get("EXA_API_KEY") or "").strip()
    if not key:
        raise ExaError("EXA_API_KEY not set; source ~/.hermes/.env")
    return key


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def query_hash(payload: Mapping[str, Any]) -> str:
    """sha256 of the canonical request payload — safe to log; doesn't leak query."""
    return hashlib.sha256(_canonical_json(payload)).hexdigest()[:16]


def _post(endpoint: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    body = _canonical_json(payload)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "x-api-key": _load_api_key(),
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not echo the response body — error pages can include the api key header.
        raise ExaError(f"Exa rejected request (HTTP {exc.code} at {endpoint})") from exc
    except urllib.error.URLError as exc:
        raise ExaError(f"Exa unreachable at {url}: {exc.reason}") from exc


def _wrap(payload: Mapping[str, Any], endpoint: str, response: Mapping[str, Any], vertical: str | None) -> dict[str, Any]:
    results = response.get("results") or []
    return {
        "results_count": len(results) if isinstance(results, list) else 0,
        "query_hash": query_hash(payload),
        "vertical": vertical,
        "exa_endpoint": endpoint,
        "data": response,
    }


# --------------------------------------------------------------------------- #
# /search — neural + keyword + structured-output retrieval
# --------------------------------------------------------------------------- #


def search_signals(
    query: str,
    *,
    domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    num_results: int = 10,
    vertical: str | None = None,
    mode: str = "auto",
    with_highlights: bool = True,
    with_text: bool = False,
    text_max_chars: int = 2000,
) -> dict[str, Any]:
    """Query Exa for relevant URLs + (optionally) snippets.

    ``mode`` accepts ``auto``, ``fast``, ``instant``, ``deep-lite``, ``deep``,
    ``deep-reasoning`` per the Exa API reference. ``auto`` is the right
    default for buyer-signal-router work — Exa picks the best path.

    ``contents`` is always populated. Highlights (token-cheap excerpts) ship
    on by default; full text is opt-in via ``with_text=True`` and capped via
    ``text_max_chars`` to keep token usage predictable in agent loops.
    """
    payload: dict[str, Any] = {
        "query": query,
        "type": mode,
        "numResults": num_results,
        "contents": {},
    }
    if with_highlights:
        payload["contents"]["highlights"] = True
    if with_text:
        payload["contents"]["text"] = {"maxCharacters": text_max_chars}
    if domains:
        payload["includeDomains"] = list(domains)
    if exclude_domains:
        payload["excludeDomains"] = list(exclude_domains)
    return _wrap(payload, "search", _post("search", payload), vertical)


def fetch_contents(
    ids_or_urls: list[str],
    *,
    with_highlights: bool = True,
    with_text: bool = False,
    text_max_chars: int = 2000,
    vertical: str | None = None,
) -> dict[str, Any]:
    """Get parsed content for URLs (or Exa result ids) already known.

    Use when URLs come from another source (database, RSS, earlier search)
    and you want clean text. On ``/contents``, ``highlights`` / ``text`` are
    top-level (not nested) per the API reference.
    """
    payload: dict[str, Any] = {"ids": list(ids_or_urls)}
    if with_highlights:
        payload["highlights"] = True
    if with_text:
        payload["text"] = {"maxCharacters": text_max_chars}
    return _wrap(payload, "contents", _post("contents", payload), vertical)
