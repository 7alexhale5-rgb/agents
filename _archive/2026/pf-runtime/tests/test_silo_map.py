"""Tests for the address -> silo mapping used by communications-triage."""

from __future__ import annotations

import pytest

from pf_runtime.communications.silo_map import (
    VALID_SILOS,
    silo_for_address,
)


def test_prettyflyforai_addresses_route_to_prettyfly() -> None:
    assert silo_for_address("alex@prettyflyforai.com") == "prettyfly"
    assert silo_for_address("info@prettyflyforai.com") == "prettyfly"


def test_kohoconsulting_routes_to_koho() -> None:
    assert silo_for_address("alex@kohoconsulting.com") == "koho"


def test_ctox_routes_to_ctox() -> None:
    assert silo_for_address("alex@ctox.com") == "ctox"


def test_yehovahbuilders_routes_to_yeh() -> None:
    assert silo_for_address("alex@yehovahbuilders.com") == "yeh"


def test_personal_gmail_override_routes_to_prettyfly() -> None:
    """The personal 7alexhale5@gmail.com address isn't on a prettyfly domain
    but is operator-owned and belongs in the prettyfly silo per the
    explicit override list in silo_map._ADDRESS_OVERRIDES."""
    assert silo_for_address("7alexhale5@gmail.com") == "prettyfly"


def test_address_lookup_is_case_insensitive() -> None:
    assert silo_for_address("ALEX@KohoConsulting.COM") == "koho"
    assert silo_for_address("Alex@PrettyFlyForAI.com") == "prettyfly"


def test_unmapped_domain_falls_back_to_default_silo() -> None:
    assert silo_for_address("someone@example.org") == "prettyfly"


def test_invalid_address_still_returns_a_valid_silo() -> None:
    """Defensive: no input should produce an out-of-set silo (PFOS would
    reject any slug not in WRITEBACK_SLUGS with invalid_silo)."""
    assert silo_for_address("not-an-email") in VALID_SILOS
    assert silo_for_address("") in VALID_SILOS


@pytest.mark.parametrize("silo", sorted(VALID_SILOS))
def test_valid_silos_set_is_non_empty(silo: str) -> None:
    assert isinstance(silo, str)
    assert silo  # no empty strings


def test_valid_silos_matches_pfos_writeback_slugs() -> None:
    """Lock the set against PFOS lib/siloAdapters/index.ts. If PFOS adds
    or removes a writeback slug, this test forces a sync."""
    expected = frozenset(
        {"yeh", "koho", "ctox", "prettyfly", "rnd", "ops", "home", "fleet", "skills"}
    )
    assert expected == VALID_SILOS
