"""Exa shim — calls ``exa_client`` then emits the contract-bound event.

Sole sanctioned path from Marin (and any future profile) to Exa. The client
itself is reachable as a library, but profile contracts should route through
``search_with_event`` so:

  - daily rate caps in ``fleet/limits.json`` are enforced
  - every Exa call lands one row in ``public.agent_events``
  - the event payload carries hashed query + counts, never raw URLs / snippets

Single function (no XOR pair needed — Exa /search and /contents are different
enough that exposing both as separate emit calls would complicate the contract).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from hermes.lib.agent_events import emit_event
from hermes.lib.exa_client import search_signals


def _hash_domains(domains: list[str] | None) -> str | None:
    """Short sha256 of the joined domain list. Avoids leaking buyer-research domain choices to PFOS."""
    if not domains:
        return None
    joined = "\n".join(sorted(domains))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def search_with_event(
    profile_dir: str | Path,
    *,
    query: str,
    domains: list[str] | None = None,
    exclude_domains: list[str] | None = None,
    num_results: int = 10,
    vertical: str | None = None,
    mode: str = "auto",
    with_highlights: bool = True,
    with_text: bool = False,
    text_max_chars: int = 2000,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Call exa_client.search_signals + emit marin.exa_query.proposed event.

    The event row carries ``results_count``, ``query_hash``, ``vertical``,
    ``exa_endpoint``, and a hashed ``domains_filter`` — never the raw URLs,
    domains, or snippets. Raw results stay local to the agent's working set.
    """
    result = search_signals(
        query,
        domains=domains,
        exclude_domains=exclude_domains,
        num_results=num_results,
        vertical=vertical,
        mode=mode,
        with_highlights=with_highlights,
        with_text=with_text,
        text_max_chars=text_max_chars,
    )

    overrides = {
        "data": {
            "results_count": result["results_count"],
            "query_hash": result["query_hash"],
            "vertical": result.get("vertical"),
            "exa_endpoint": result["exa_endpoint"],
            "exa_mode": mode,
            "domains_filter": _hash_domains(domains),
        }
    }
    emission = emit_event(profile_dir, "marin.exa_search", overrides=overrides, dry_run=dry_run)
    return {"searched": result, "event": emission}
