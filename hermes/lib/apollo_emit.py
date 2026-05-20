"""Apollo shim — calls ``apollo_client`` then emits the contract-bound event.

This is the only sanctioned path for Marin (and any future profile) to reach
Apollo. The client itself is reachable as a library, but profile contracts
should route through the functions here so:

  - daily rate caps in ``fleet/limits.json`` are enforced
  - every Apollo call lands one row in ``public.agent_events``
  - the event payload carries hashed query + counts, never raw targets / PII

Two functions, one per Marin contract entry:

    enrich_list_with_event       → marin.apollo_enrich_list
    discover_prospects_with_event → marin.apollo_discover_prospects

Both raise ``RateLimitExceeded`` (from agent_events) when the daily cap is
hit; callers should treat that as queue-for-tomorrow, not a bug.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from hermes.lib.agent_events import emit_event
from hermes.lib.apollo_client import (
    bulk_enrich_organizations,
    bulk_enrich_people,
    search_companies,
    search_people,
)


def enrich_list_with_event(
    profile_dir: str | Path,
    *,
    people: list[Mapping[str, Any]] | None = None,
    domains: list[str] | None = None,
    vertical: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Enrich a known list (people OR domains) and emit one agent_event row.

    Exactly one of ``people`` or ``domains`` must be set. Mixing the two
    surfaces from a single tool call would dilute the event's
    ``data.apollo_endpoint`` — split such workflows into two calls.
    """
    if (people is None) == (domains is None):
        raise ValueError("enrich_list_with_event requires exactly one of people= or domains=")

    result = (
        bulk_enrich_people(people, vertical=vertical)
        if people is not None
        else bulk_enrich_organizations(domains or [], vertical=vertical)
    )

    overrides = {
        "data": {
            "results_count": result["results_count"],
            "query_hash": result["query_hash"],
            "vertical": result.get("vertical"),
            "apollo_endpoint": result["apollo_endpoint"],
        }
    }
    emission = emit_event(profile_dir, "marin.apollo_enrich_list", overrides=overrides, dry_run=dry_run)
    return {"enriched": result, "event": emission}


def discover_prospects_with_event(
    profile_dir: str | Path,
    *,
    people_filters: Mapping[str, Any] | None = None,
    company_filters: Mapping[str, Any] | None = None,
    vertical: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Discover prospects (people OR companies) and emit one agent_event row.

    Mirrors ``enrich_list_with_event`` — exactly one filter surface per call.
    """
    if (people_filters is None) == (company_filters is None):
        raise ValueError(
            "discover_prospects_with_event requires exactly one of people_filters= or company_filters="
        )

    result = (
        search_people(people_filters, vertical=vertical)
        if people_filters is not None
        else search_companies(company_filters or {}, vertical=vertical)
    )

    overrides = {
        "data": {
            "results_count": result["results_count"],
            "query_hash": result["query_hash"],
            "vertical": result.get("vertical"),
            "apollo_endpoint": result["apollo_endpoint"],
        }
    }
    emission = emit_event(profile_dir, "marin.apollo_discover_prospects", overrides=overrides, dry_run=dry_run)
    return {"discovered": result, "event": emission}
