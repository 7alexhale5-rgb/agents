"""Account registry loader for communications-triage v1.

Loads a YAML registry shaped like
``marketplace/manifests/communications-triage/account-registry.example.yaml``
and validates it against the SKU manifest's ``provider_matrix``. Refuses any
account that asks for a forbidden_v1 scope or for SMTP send on IMAP. Credential
material lives in env vars, not in the registry file — the loader records
which accounts have credentials and which need them, then a separate client
layer connects.

This module enforces v1 read+propose at the configuration boundary. Even if
``policy.assert_v1_action_allowed`` were bypassed, an account that requested
``gmail.modify`` (or any forbidden scope) would never load.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from pf_runtime.communications.schema import AccountConfig, Provider

log = logging.getLogger(__name__)


class RegistryError(Exception):
    """Base class for account registry errors."""


class RegistryParseError(RegistryError):
    """YAML missing, malformed, or top-level shape unexpected."""


class RegistryValidationError(RegistryError):
    """Required field missing, value type wrong, or contract violation."""


class ScopeViolationError(RegistryError):
    """Account requested a scope on the manifest's forbidden_v1 list."""


@dataclass(frozen=True)
class IMAPSettings:
    """Provider-specific connection settings for IMAP accounts."""

    port: int = 993
    ssl: bool = True
    smtp_enabled_v1: bool = False


@dataclass(frozen=True)
class RegistryEntry:
    """One loaded account plus the credential-presence flag and IMAP extras."""

    account: AccountConfig
    imap: IMAPSettings | None = None
    credentials_present: bool = False


@dataclass(frozen=True)
class AccountRegistry:
    """Frozen collection of loaded registry entries."""

    entries: tuple[RegistryEntry, ...]

    @classmethod
    def load(
        cls,
        yaml_path: Path,
        *,
        manifest_path: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> AccountRegistry:
        """Parse ``yaml_path`` and return a frozen registry.

        ``manifest_path`` (when provided) is the SKU manifest whose
        ``provider_matrix`` defines per-provider scope whitelists/blacklists
        and the IMAP transport contract. ``env`` defaults to ``os.environ``;
        tests pass an explicit dict.
        """
        env_map = _resolve_env(env)
        if not yaml_path.is_file():
            raise RegistryParseError(f"registry not found: {yaml_path}")

        try:
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise RegistryParseError(f"YAML parse failed: {exc}") from exc

        if not isinstance(data, dict) or "accounts" not in data:
            raise RegistryParseError("registry must be a mapping with key 'accounts'")
        raw_accounts = data["accounts"]
        if not isinstance(raw_accounts, list):
            raise RegistryParseError("'accounts' must be a list")

        manifest_matrix = _load_manifest_matrix(manifest_path)

        entries = tuple(
            _entry_from_raw(raw, idx=idx, manifest_matrix=manifest_matrix, env=env_map)
            for idx, raw in enumerate(raw_accounts)
        )
        return cls(entries=entries)

    def get(self, account_id: str) -> RegistryEntry:
        """Return the entry with ``account_id``; raise ``KeyError`` if absent."""
        for entry in self.entries:
            if entry.account.account_id == account_id:
                return entry
        raise KeyError(account_id)

    def with_credentials(self) -> Iterator[RegistryEntry]:
        """Iterate only entries whose credential env var was present at load."""
        return (e for e in self.entries if e.credentials_present)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_env(env: Mapping[str, str] | None) -> Mapping[str, str]:
    if env is not None:
        return env
    import os

    return os.environ


_ENV_PREFIX: dict[Provider, str] = {
    Provider.GOOGLE_MAIL: "PF_GMAIL_TOKEN_",
    Provider.GOOGLE_CALENDAR: "PF_GMAIL_TOKEN_",  # same OAuth grant
    Provider.MICROSOFT_GRAPH: "PF_GRAPH_TOKEN_",
    Provider.IMAP_HOSTGATOR: "PF_IMAP_PASSWORD_",
}


def _credential_env_name(provider: Provider, account_id: str) -> str:
    prefix = _ENV_PREFIX[provider]
    safe = account_id.upper().replace("-", "_")
    return f"{prefix}{safe}"


_PROVIDER_MATRIX_KEY: dict[Provider, str] = {
    Provider.GOOGLE_MAIL: "gmail",
    Provider.GOOGLE_CALENDAR: "google_calendar",
    Provider.MICROSOFT_GRAPH: "microsoft_graph",
    Provider.IMAP_HOSTGATOR: "hostgator_imap",
}


def _load_manifest_matrix(
    manifest_path: Path | None,
) -> dict[str, dict[str, Any]] | None:
    if manifest_path is None:
        return None
    if not manifest_path.is_file():
        raise RegistryValidationError(f"manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RegistryValidationError(f"manifest JSON invalid: {exc}") from exc
    matrix = manifest.get("provider_matrix")
    if not isinstance(matrix, dict):
        raise RegistryValidationError("manifest missing provider_matrix")
    return matrix


def _entry_from_raw(
    raw: Any,
    *,
    idx: int,
    manifest_matrix: dict[str, dict[str, Any]] | None,
    env: Mapping[str, str],
) -> RegistryEntry:
    if not isinstance(raw, dict):
        raise RegistryValidationError(f"account #{idx}: must be a mapping")

    for required in ("account_id", "provider", "address"):
        if required not in raw:
            raise RegistryValidationError(
                f"account #{idx}: missing required field '{required}'"
            )

    try:
        provider = Provider(raw["provider"])
    except ValueError as exc:
        raise RegistryValidationError(
            f"account #{idx}: unknown provider '{raw['provider']}'"
        ) from exc

    scopes = tuple(raw.get("scopes") or ())
    if not all(isinstance(s, str) for s in scopes):
        raise RegistryValidationError(
            f"account {raw['account_id']}: scopes must be strings"
        )

    if not bool(raw.get("read_only", True)):
        raise RegistryValidationError(
            f"account {raw['account_id']}: read_only must be true in v1"
        )

    if manifest_matrix is not None:
        _validate_scopes_against_matrix(
            account_id=str(raw["account_id"]),
            provider=provider,
            scopes=scopes,
            matrix=manifest_matrix,
        )

    imap_settings: IMAPSettings | None = None
    if provider == Provider.IMAP_HOSTGATOR:
        imap_settings = _imap_settings_from_raw(
            raw, account_id=str(raw["account_id"]), manifest_matrix=manifest_matrix
        )

    account = AccountConfig(
        account_id=str(raw["account_id"]),
        provider=provider,
        address=str(raw["address"]),
        display_name=str(raw.get("display_name", "")),
        scopes=scopes,
        read_only=True,
    )

    env_name = _credential_env_name(provider, account.account_id)
    creds_present = bool(env.get(env_name))
    if not creds_present:
        log.warning(
            "account_registry: missing credential env var %s for account %s; "
            "loaded without credentials",
            env_name,
            account.account_id,
        )

    return RegistryEntry(
        account=account, imap=imap_settings, credentials_present=creds_present
    )


def _imap_settings_from_raw(
    raw: dict[str, Any],
    *,
    account_id: str,
    manifest_matrix: dict[str, dict[str, Any]] | None,
) -> IMAPSettings:
    imap_raw = raw.get("imap") or {}
    if not isinstance(imap_raw, dict):
        raise RegistryValidationError(f"account {account_id}: 'imap' must be a mapping")
    port = int(imap_raw.get("port", 993))
    ssl = bool(imap_raw.get("ssl", True))
    smtp_enabled_v1 = bool(raw.get("smtp_enabled_v1", False))
    if smtp_enabled_v1:
        raise RegistryValidationError(
            f"account {account_id}: smtp_enabled_v1 must be false in v1"
        )
    if manifest_matrix is not None:
        _validate_imap_transport(
            account_id=account_id, port=port, ssl=ssl, matrix=manifest_matrix
        )
    return IMAPSettings(port=port, ssl=ssl, smtp_enabled_v1=smtp_enabled_v1)


def _validate_scopes_against_matrix(
    *,
    account_id: str,
    provider: Provider,
    scopes: tuple[str, ...],
    matrix: dict[str, dict[str, Any]],
) -> None:
    matrix_key = _PROVIDER_MATRIX_KEY.get(provider)
    if matrix_key is None or matrix_key not in matrix:
        return
    spec = matrix[matrix_key]
    forbidden = set(spec.get("forbidden_v1_scopes", ()))
    if not forbidden:
        return
    violating = [s for s in scopes if s in forbidden]
    if violating:
        raise ScopeViolationError(
            f"account {account_id} ({provider.value}) requests forbidden v1 "
            f"scope(s): {violating}"
        )


def _validate_imap_transport(
    *,
    account_id: str,
    port: int,
    ssl: bool,
    matrix: dict[str, dict[str, Any]],
) -> None:
    spec = matrix.get("hostgator_imap")
    if not spec:
        return
    transport = spec.get("v1_transport")
    if transport == "imap_ssl_993" and (port != 993 or not ssl):
        raise RegistryValidationError(
            f"account {account_id}: manifest requires imap_ssl_993; "
            f"got port={port} ssl={ssl}"
        )
