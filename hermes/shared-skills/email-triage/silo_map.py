"""Address -> silo mapping for communications-triage PFOS routing.

Each connected mail account belongs to one silo on the PFOS side. The
silo determines which ``/api/silos/<slug>/agent-action`` URL receives
the triage emission for that account. Mapping is deterministic from
the email domain plus a small explicit override list for cases where
domain alone isn't enough (e.g. personal Gmail tied to Alex's main
prettyfly workstream).

The set of legal silo slugs is enforced server-side by PFOS via
``isWritebackSlug`` in ``lib/siloAdapters/index.ts``. This module mirrors
that set so PF Runtime never POSTs to an invalid silo URL.
"""

from __future__ import annotations

VALID_SILOS: frozenset[str] = frozenset(
    {"yeh", "koho", "ctox", "prettyfly", "rnd", "ops", "home", "fleet", "skills"}
)

_DEFAULT_SILO = "prettyfly"


_DOMAIN_SILO: dict[str, str] = {
    "prettyflyforai.com": "prettyfly",
    "ctox.com": "ctox",
    "kohoconsulting.com": "koho",
    "yehovahbuilders.com": "yeh",
}


_ADDRESS_OVERRIDES: dict[str, str] = {
    "7alexhale5@gmail.com": "prettyfly",
}


def silo_for_address(address: str) -> str:
    """Return the PFOS silo slug for ``address``.

    Lookup order:
      1. Exact-address match in :data:`_ADDRESS_OVERRIDES`.
      2. Domain match in :data:`_DOMAIN_SILO`.
      3. :data:`_DEFAULT_SILO` (``prettyfly``).

    Always returns a member of :data:`VALID_SILOS`; the default is set
    only for unmapped addresses so the runtime can't synthesise a slug
    PFOS would refuse with ``invalid_silo``.
    """
    normalized = address.strip().lower()
    if normalized in _ADDRESS_OVERRIDES:
        return _ADDRESS_OVERRIDES[normalized]
    if "@" in normalized:
        domain = normalized.split("@", 1)[1]
        if domain in _DOMAIN_SILO:
            return _DOMAIN_SILO[domain]
    return _DEFAULT_SILO
