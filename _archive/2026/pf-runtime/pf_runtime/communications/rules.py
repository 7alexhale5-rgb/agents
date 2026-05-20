"""Per-source triage rules loader for the operator protocol.

Loads a YAML file shaped like ``config/triage-rules.example.yaml`` and
exposes match helpers consumed by :mod:`priority` and :mod:`filing`.

Schema (per silo):

    silos:
      <silo>:
        vips:
          p0:    list of address-or-domain patterns; matched senders escalate to P0
          any:   list of patterns; matched senders bump priority floor to P1
        role_hints:
          - { matches: "<pattern>", label_suffix: "<role>" }

Patterns support:
- Exact address (``josh@kohoconsulting.com``)
- Domain wildcard (``*@kohoconsulting.com``)
- Local-part wildcard (``noreply@*``)

The loader is intentionally permissive about missing rules — a silo
with no entries returns "no match" everywhere, which the priority and
filing layers handle by falling back to defaults. The example YAML
ships with sane defaults for all 4 personal-profile silos.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger(__name__)


class RulesError(Exception):
    """Base class for triage-rules errors."""


class RulesParseError(RulesError):
    """YAML missing, malformed, or top-level shape unexpected."""


class RulesValidationError(RulesError):
    """Required field missing, value type wrong, or pattern invalid."""


@dataclass(frozen=True)
class RoleHint:
    """One ``matches -> label_suffix`` mapping inside a silo's role_hints."""

    pattern: str
    label_suffix: str


@dataclass(frozen=True)
class SiloRules:
    """All rules for one silo (koho, ctox, yeh, prettyfly)."""

    vips_p0: tuple[str, ...] = ()
    vips_any: tuple[str, ...] = ()
    role_hints: tuple[RoleHint, ...] = ()


@dataclass(frozen=True)
class TriageRules:
    """All loaded rules across all silos."""

    silos: Mapping[str, SiloRules] = field(default_factory=dict)

    @classmethod
    def empty(cls) -> TriageRules:
        return cls(silos={})

    def for_silo(self, silo: str) -> SiloRules:
        """Return the silo's rules; empty SiloRules if the silo is unknown."""
        return self.silos.get(silo, SiloRules())

    @classmethod
    def load(cls, yaml_path: Path | None) -> TriageRules:
        """Parse ``yaml_path`` and return the rules.

        ``yaml_path`` of ``None`` or a missing file returns
        :meth:`empty` with a WARN log — the cycle still runs, every
        message lands at P3 with no proposed label.
        """
        if yaml_path is None or not yaml_path.is_file():
            log.warning(
                "triage_rules: file not found at %s; running with empty rules",
                yaml_path,
            )
            return cls.empty()
        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RulesParseError(f"YAML parse failed: {exc}") from exc

        if data is None:
            return cls.empty()
        if not isinstance(data, dict):
            raise RulesParseError("rules root must be a mapping")
        raw_silos = data.get("silos") or {}
        if not isinstance(raw_silos, dict):
            raise RulesValidationError("'silos' must be a mapping")

        loaded: dict[str, SiloRules] = {}
        for silo_name, silo_raw in raw_silos.items():
            if not isinstance(silo_raw, dict):
                raise RulesValidationError(
                    f"silo {silo_name!r}: must be a mapping"
                )
            loaded[str(silo_name)] = _silo_from_raw(str(silo_name), silo_raw)
        return cls(silos=loaded)


def matches_pattern(pattern: str, address: str) -> bool:
    """Return True iff ``address`` matches ``pattern``.

    Match rules (case-insensitive):
    - Exact: ``josh@kohoconsulting.com`` matches only ``josh@kohoconsulting.com``.
    - Domain wildcard: ``*@kohoconsulting.com`` matches anything @ that domain.
    - Local-part wildcard: ``noreply@*`` matches ``noreply@`` followed by any domain.
    - Full wildcard: ``*@*`` matches any address (use sparingly — kills specificity).
    """
    if not pattern or not address:
        return False
    pat = pattern.strip().lower()
    addr = address.strip().lower()
    # Strip display-name wrapping ("Alex Hale <alex@example.com>" -> "alex@example.com").
    if "<" in addr and ">" in addr:
        start = addr.find("<")
        end = addr.find(">", start + 1)
        if start != -1 and end != -1:
            addr = addr[start + 1 : end]

    if "@" not in pat:
        # Treat bare patterns as a domain wildcard (`kohoconsulting.com` -> `*@kohoconsulting.com`).
        pat = f"*@{pat}"

    pat_local, pat_domain = pat.split("@", 1)
    if "@" not in addr:
        return False
    addr_local, addr_domain = addr.split("@", 1)

    if pat_local != "*" and pat_local != addr_local:
        return False
    return pat_domain in ("*", addr_domain)


def first_role_match(hints: tuple[RoleHint, ...], sender: str) -> str | None:
    """Return the first ``label_suffix`` whose pattern matches ``sender``."""
    for hint in hints:
        if matches_pattern(hint.pattern, sender):
            return hint.label_suffix
    return None


def sender_is_vip(silo: SiloRules, sender: str, *, tier: str) -> bool:
    """Return True iff ``sender`` matches any pattern in the tier list.

    ``tier`` is ``"p0"`` or ``"any"`` (the two VIP escalation tiers).
    """
    if tier == "p0":
        patterns = silo.vips_p0
    elif tier == "any":
        patterns = silo.vips_any
    else:
        raise ValueError(f"unknown vip tier: {tier!r}")
    return any(matches_pattern(p, sender) for p in patterns)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _silo_from_raw(silo_name: str, raw: dict[str, Any]) -> SiloRules:
    vips_raw = raw.get("vips") or {}
    if not isinstance(vips_raw, dict):
        raise RulesValidationError(f"silo {silo_name!r}: 'vips' must be a mapping")

    p0 = _string_tuple(vips_raw.get("p0"), context=f"{silo_name}.vips.p0")
    any_tier = _string_tuple(vips_raw.get("any"), context=f"{silo_name}.vips.any")

    hints_raw = raw.get("role_hints") or []
    if not isinstance(hints_raw, list):
        raise RulesValidationError(f"silo {silo_name!r}: 'role_hints' must be a list")
    hints: list[RoleHint] = []
    for idx, hint_raw in enumerate(hints_raw):
        if not isinstance(hint_raw, dict):
            raise RulesValidationError(
                f"silo {silo_name!r}: role_hints[{idx}] must be a mapping"
            )
        pattern = hint_raw.get("matches")
        suffix = hint_raw.get("label_suffix")
        if not isinstance(pattern, str) or not pattern.strip():
            raise RulesValidationError(
                f"silo {silo_name!r}: role_hints[{idx}].matches must be a non-empty string"
            )
        if not isinstance(suffix, str) or not suffix.strip():
            raise RulesValidationError(
                f"silo {silo_name!r}: role_hints[{idx}].label_suffix must be a non-empty string"
            )
        hints.append(RoleHint(pattern=pattern.strip(), label_suffix=suffix.strip()))

    if not p0 and not any_tier and not hints:
        log.warning(
            "triage_rules: silo %r has no vips and no role_hints; messages "
            "from this silo will land at P3 with no proposed label",
            silo_name,
        )

    return SiloRules(vips_p0=p0, vips_any=any_tier, role_hints=tuple(hints))


def _string_tuple(value: Any, *, context: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise RulesValidationError(f"{context}: must be a list (got {type(value).__name__})")
    out: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise RulesValidationError(
                f"{context}[{idx}]: must be a non-empty string"
            )
        out.append(item.strip())
    return tuple(out)
