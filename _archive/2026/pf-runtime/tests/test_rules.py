"""Tests for the triage-rules YAML loader + pattern match helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from pf_runtime.communications.rules import (
    RoleHint,
    RulesParseError,
    RulesValidationError,
    SiloRules,
    TriageRules,
    first_role_match,
    matches_pattern,
    sender_is_vip,
)


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# matches_pattern
# ---------------------------------------------------------------------------


def test_exact_address_match() -> None:
    assert matches_pattern("josh@kohoconsulting.com", "josh@kohoconsulting.com")
    assert not matches_pattern("josh@kohoconsulting.com", "alex@kohoconsulting.com")


def test_domain_wildcard_match() -> None:
    assert matches_pattern("*@kohoconsulting.com", "alex@kohoconsulting.com")
    assert matches_pattern("*@kohoconsulting.com", "noreply@kohoconsulting.com")
    assert not matches_pattern("*@kohoconsulting.com", "alex@example.com")


def test_local_part_wildcard_match() -> None:
    assert matches_pattern("noreply@*", "noreply@anywhere.com")
    assert not matches_pattern("noreply@*", "alex@anywhere.com")


def test_full_wildcard_matches_everything() -> None:
    assert matches_pattern("*@*", "anyone@anywhere.com")


def test_bare_domain_shorthand_works_as_domain_wildcard() -> None:
    assert matches_pattern("kohoconsulting.com", "alex@kohoconsulting.com")
    assert not matches_pattern("kohoconsulting.com", "alex@example.com")


def test_match_is_case_insensitive() -> None:
    assert matches_pattern("Josh@KohoConsulting.com", "josh@kohoconsulting.com")


def test_match_strips_display_name_wrap() -> None:
    assert matches_pattern(
        "*@kohoconsulting.com", "Josh Smith <josh@kohoconsulting.com>"
    )


def test_match_returns_false_for_empty_inputs() -> None:
    assert not matches_pattern("", "alex@example.com")
    assert not matches_pattern("*@*", "")


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


def test_load_missing_file_returns_empty(tmp_path: Path) -> None:
    rules = TriageRules.load(tmp_path / "missing.yaml")
    assert rules.silos == {}


def test_load_none_path_returns_empty() -> None:
    rules = TriageRules.load(None)
    assert rules.silos == {}


def test_load_minimal_valid(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "rules.yaml",
        (
            "silos:\n"
            "  koho:\n"
            "    vips:\n"
            "      p0: []\n"
            "      any:\n"
            "        - josh@kohoconsulting.com\n"
            "    role_hints:\n"
            "      - { matches: 'josh@kohoconsulting.com', label_suffix: 'Clients/Josh' }\n"
        ),
    )
    rules = TriageRules.load(yaml_path)
    koho = rules.for_silo("koho")
    assert koho.vips_any == ("josh@kohoconsulting.com",)
    assert koho.role_hints == (
        RoleHint(pattern="josh@kohoconsulting.com", label_suffix="Clients/Josh"),
    )


def test_load_unknown_silo_returns_empty_silo_rules() -> None:
    rules = TriageRules.empty()
    assert rules.for_silo("koho") == SiloRules()


def test_load_invalid_yaml_raises(tmp_path: Path) -> None:
    yaml_path = _write(tmp_path / "bad.yaml", "not: a: list:\n  - missing colon")
    with pytest.raises(RulesParseError):
        TriageRules.load(yaml_path)


def test_load_rejects_non_mapping_root(tmp_path: Path) -> None:
    yaml_path = _write(tmp_path / "list.yaml", "- one\n- two\n")
    with pytest.raises(RulesParseError):
        TriageRules.load(yaml_path)


def test_load_rejects_vips_p0_non_string(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "rules.yaml",
        "silos:\n  koho:\n    vips:\n      p0: [42]\n      any: []\n",
    )
    with pytest.raises(RulesValidationError):
        TriageRules.load(yaml_path)


def test_load_rejects_role_hint_without_label_suffix(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "rules.yaml",
        (
            "silos:\n  koho:\n    vips:\n      p0: []\n      any: []\n"
            "    role_hints:\n      - { matches: 'josh@kohoconsulting.com' }\n"
        ),
    )
    with pytest.raises(RulesValidationError):
        TriageRules.load(yaml_path)


def test_ships_with_example_yaml() -> None:
    """The shipped example must parse with no errors."""
    repo_root = Path(__file__).resolve().parents[2]
    example = repo_root / "pf-runtime" / "config" / "triage-rules.example.yaml"
    rules = TriageRules.load(example)
    # All 4 personal-profile silos should be present.
    for silo in ("koho", "ctox", "yeh", "prettyfly"):
        assert silo in rules.silos


# ---------------------------------------------------------------------------
# Higher-level helpers
# ---------------------------------------------------------------------------


def test_sender_is_vip_any_tier() -> None:
    silo = SiloRules(vips_any=("*@kohoconsulting.com",))
    assert sender_is_vip(silo, "josh@kohoconsulting.com", tier="any")
    assert not sender_is_vip(silo, "stranger@example.com", tier="any")


def test_sender_is_vip_p0_tier_distinct_from_any() -> None:
    silo = SiloRules(
        vips_p0=("emergency@example.com",),
        vips_any=("normal@example.com",),
    )
    assert sender_is_vip(silo, "emergency@example.com", tier="p0")
    assert not sender_is_vip(silo, "normal@example.com", tier="p0")
    assert sender_is_vip(silo, "normal@example.com", tier="any")


def test_sender_is_vip_rejects_unknown_tier() -> None:
    silo = SiloRules()
    with pytest.raises(ValueError):
        sender_is_vip(silo, "alex@example.com", tier="bogus")


def test_first_role_match_returns_first_winner() -> None:
    hints = (
        RoleHint(pattern="josh@kohoconsulting.com", label_suffix="Clients/Josh"),
        RoleHint(pattern="*@kohoconsulting.com", label_suffix="Internal"),
    )
    # Specific pattern first → wins over the general one.
    assert first_role_match(hints, "josh@kohoconsulting.com") == "Clients/Josh"
    assert first_role_match(hints, "alex@kohoconsulting.com") == "Internal"
    assert first_role_match(hints, "alex@example.com") is None
