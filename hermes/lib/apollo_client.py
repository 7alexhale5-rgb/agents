"""Apollo.io REST client — direct HTTPS, stdlib-only.

Reads the API key from ``~/Projects/apollo-mcp/.env`` (single source of truth
shared with the Claude Code Apollo MCP server) or the ``APOLLO_API_KEY`` env
var. The MCP server and this client both source the same key — if you rotate
one, the other rotates with it.

The four exposed call sites map to Marin's two contract-bound tools:

    marin.apollo_enrich_list       → bulk_enrich_people / bulk_enrich_organizations
    marin.apollo_discover_prospects → search_people / search_companies

Every call returns a dict with ``results_count``, ``query_hash``, optional
``vertical``, and the raw Apollo response under ``data``. The query_hash is a
deterministic sha256 of the canonical request payload — safe to log in an
agent_event row without leaking the actual query, targets, or filters.

No retry loop, no rate limiter — Apollo's 429 surfaces as ``ApolloError``,
which the caller can decide to back off on. Daily-cap enforcement lives in
``agent_events._check_and_increment`` (emit-side, not call-side).
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

API_BASE = "https://api.apollo.io/v1"
_ENV_PATH = Path.home() / "Projects" / "apollo-mcp" / ".env"
_REQUEST_TIMEOUT_SECONDS = 30


class ApolloError(RuntimeError):
    """Raised when Apollo returns a non-2xx response or the API key is missing."""


def _load_api_key() -> str:
    """Read APOLLO_API_KEY from env var first, then ``~/Projects/apollo-mcp/.env``."""
    key = (os.environ.get("APOLLO_API_KEY") or "").strip()
    if key:
        return key
    if _ENV_PATH.exists():
        for line in _ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == "APOLLO_API_KEY":
                # strip optional surrounding quotes
                return v.strip().strip('"').strip("'")
    raise ApolloError(
        "APOLLO_API_KEY not found in env or ~/Projects/apollo-mcp/.env"
    )


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    """sort_keys + no whitespace — same bytes regardless of dict insertion order."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def query_hash(payload: Mapping[str, Any]) -> str:
    """sha256 of the canonical request payload. Safe to log; doesn't leak query."""
    return hashlib.sha256(_canonical_json(payload)).hexdigest()[:16]


def _post(endpoint: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """POST to ``API_BASE/endpoint`` with X-Api-Key header. Raises ApolloError on non-2xx."""
    url = f"{API_BASE}/{endpoint.lstrip('/')}"
    body = _canonical_json(payload)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "X-Api-Key": _load_api_key(),
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # Do not surface response body — it may echo the X-Api-Key on misconfigured proxies.
        raise ApolloError(f"Apollo rejected request (HTTP {exc.code} at {endpoint})") from exc
    except urllib.error.URLError as exc:
        raise ApolloError(f"Apollo unreachable at {url}: {exc.reason}") from exc


def _wrap(payload: Mapping[str, Any], endpoint: str, response: Mapping[str, Any], result_key: str, vertical: str | None) -> dict[str, Any]:
    """Pack the call result into the contract-stable dict shape."""
    results = response.get(result_key) or []
    return {
        "results_count": len(results) if isinstance(results, list) else 0,
        "query_hash": query_hash(payload),
        "vertical": vertical,
        "apollo_endpoint": endpoint,
        "data": response,
    }


# --------------------------------------------------------------------------- #
# Enrichment — known leads → verified emails + firmographics
# --------------------------------------------------------------------------- #


def bulk_enrich_people(people: list[Mapping[str, Any]], vertical: str | None = None) -> dict[str, Any]:
    """Enrich up to 10 known people with verified work email + firmographics.

    Each person dict accepts (any subset of): ``first_name``, ``last_name``,
    ``organization_name``, ``linkedin_url``, ``email``, ``domain``.

    Returns ``{results_count, query_hash, vertical, apollo_endpoint, data}``.
    """
    payload: dict[str, Any] = {"details": list(people)}
    return _wrap(payload, "people/bulk_match", _post("people/bulk_match", payload), "matches", vertical)


def bulk_enrich_organizations(domains: list[str], vertical: str | None = None) -> dict[str, Any]:
    """Enrich up to 10 organizations by domain. Returns the same envelope."""
    payload: dict[str, Any] = {"domains": list(domains)}
    return _wrap(payload, "organizations/bulk_enrich", _post("organizations/bulk_enrich", payload), "organizations", vertical)


# --------------------------------------------------------------------------- #
# Discovery — filter-driven prospect search
# --------------------------------------------------------------------------- #


def search_people(filters: Mapping[str, Any], vertical: str | None = None) -> dict[str, Any]:
    """Discover new prospects from filters.

    Accepted filters (subset of Apollo's API): ``person_titles``,
    ``organization_domains``, ``person_locations``, ``person_seniorities``,
    ``q_keywords``, ``page``, ``per_page``.
    """
    payload = dict(filters)
    return _wrap(payload, "mixed_people/search", _post("mixed_people/search", payload), "people", vertical)


def search_companies(filters: Mapping[str, Any], vertical: str | None = None) -> dict[str, Any]:
    """Discover companies from filters (size, industry, location, funding stage, etc.)."""
    payload = dict(filters)
    return _wrap(payload, "mixed_companies/search", _post("mixed_companies/search", payload), "organizations", vertical)
