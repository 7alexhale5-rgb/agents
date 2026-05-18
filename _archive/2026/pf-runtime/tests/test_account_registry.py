"""Account registry loader tests (Slice 1).

Covers YAML parsing, scope-whitelist enforcement against the marketplace
manifest, IMAP transport validation, env-based credential resolution, and
lookup behavior. The loader stays read+propose-only: it cannot accept a
forbidden_v1 scope or an SMTP-enabled v1 account even if the YAML asks.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pf_runtime.communications.account_registry import (
    AccountRegistry,
    RegistryParseError,
    RegistryValidationError,
    ScopeViolationError,
)
from pf_runtime.communications.schema import Provider

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_REGISTRY = (
    REPO_ROOT / "marketplace" / "manifests" / "communications-triage" / "account-registry.example.yaml"
)
MANIFEST = (
    REPO_ROOT / "marketplace" / "manifests" / "communications-triage" / "manifest.json"
)


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def test_load_example_registry_without_manifest() -> None:
    registry = AccountRegistry.load(EXAMPLE_REGISTRY, env={})
    assert len(registry.entries) == 7
    providers = [e.account.provider for e in registry.entries]
    assert providers.count(Provider.GOOGLE_MAIL) == 5
    assert providers.count(Provider.MICROSOFT_GRAPH) == 1
    assert providers.count(Provider.IMAP_HOSTGATOR) == 1


def test_load_example_registry_with_manifest_passes_scope_check() -> None:
    registry = AccountRegistry.load(EXAMPLE_REGISTRY, manifest_path=MANIFEST, env={})
    assert len(registry.entries) == 7


def test_rejects_forbidden_scope(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: bad-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.modify\n"
            "    read_only: true\n"
        ),
    )
    with pytest.raises(ScopeViolationError) as exc:
        AccountRegistry.load(yaml_path, manifest_path=MANIFEST, env={})
    assert "gmail.modify" in str(exc.value)


def test_rejects_missing_required_field(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - provider: google_mail\n"
            "    address: alex@example.com\n"
        ),
    )
    with pytest.raises(RegistryValidationError) as exc:
        AccountRegistry.load(yaml_path, env={})
    assert "account_id" in str(exc.value)


def test_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RegistryParseError):
        AccountRegistry.load(tmp_path / "missing.yaml", env={})


def test_rejects_bad_yaml(tmp_path: Path) -> None:
    yaml_path = _write(tmp_path / "bad.yaml", "not: a: list:\n  - missing colon")
    with pytest.raises(RegistryParseError):
        AccountRegistry.load(yaml_path, env={})


def test_rejects_unknown_provider(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: bad-provider\n"
            "    provider: pigeon_mail\n"
            "    address: alex@example.com\n"
        ),
    )
    with pytest.raises(RegistryValidationError) as exc:
        AccountRegistry.load(yaml_path, env={})
    assert "pigeon_mail" in str(exc.value)


def test_imap_transport_must_be_993_ssl(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: bad-imap\n"
            "    provider: imap_hostgator\n"
            "    address: alex@example.com\n"
            "    imap:\n"
            "      port: 143\n"
            "      ssl: false\n"
            "    smtp_enabled_v1: false\n"
            "    read_only: true\n"
        ),
    )
    with pytest.raises(RegistryValidationError) as exc:
        AccountRegistry.load(yaml_path, manifest_path=MANIFEST, env={})
    assert "imap_ssl_993" in str(exc.value)


def test_imap_smtp_v1_must_be_false(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: bad-imap\n"
            "    provider: imap_hostgator\n"
            "    address: alex@example.com\n"
            "    imap:\n"
            "      port: 993\n"
            "      ssl: true\n"
            "    smtp_enabled_v1: true\n"
            "    read_only: true\n"
        ),
    )
    with pytest.raises(RegistryValidationError) as exc:
        AccountRegistry.load(yaml_path, env={})
    assert "smtp_enabled_v1" in str(exc.value)


def test_credentials_present_when_env_set(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
    )
    registry = AccountRegistry.load(yaml_path, env={"PF_GMAIL_TOKEN_GMAIL_1": "abc123"})
    assert registry.entries[0].credentials_present is True


def test_credentials_missing_logs_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
    )
    with caplog.at_level("WARNING"):
        registry = AccountRegistry.load(yaml_path, env={})
    assert registry.entries[0].credentials_present is False
    assert any("PF_GMAIL_TOKEN_GMAIL_1" in r.message for r in caplog.records)


def test_with_credentials_filters(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: a\n"
            "    provider: google_mail\n"
            "    address: a@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
            "  - account_id: b\n"
            "    provider: google_mail\n"
            "    address: b@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
            "  - account_id: c\n"
            "    provider: google_mail\n"
            "    address: c@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
    )
    registry = AccountRegistry.load(
        yaml_path, env={"PF_GMAIL_TOKEN_A": "x", "PF_GMAIL_TOKEN_C": "y"}
    )
    with_creds = list(registry.with_credentials())
    assert len(with_creds) == 2
    assert {e.account.account_id for e in with_creds} == {"a", "c"}


def test_get_known_account(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
    )
    registry = AccountRegistry.load(yaml_path, env={})
    entry = registry.get("gmail-1")
    assert entry.account.address == "alex@example.com"


def test_get_unknown_raises_keyerror(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: true\n"
        ),
    )
    registry = AccountRegistry.load(yaml_path, env={})
    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_read_only_must_be_true(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: gmail-1\n"
            "    provider: google_mail\n"
            "    address: alex@example.com\n"
            "    scopes:\n"
            "      - https://www.googleapis.com/auth/gmail.readonly\n"
            "    read_only: false\n"
        ),
    )
    with pytest.raises(RegistryValidationError) as exc:
        AccountRegistry.load(yaml_path, env={})
    assert "read_only" in str(exc.value)


def test_imap_entry_carries_settings(tmp_path: Path) -> None:
    yaml_path = _write(
        tmp_path / "registry.yaml",
        (
            "accounts:\n"
            "  - account_id: imap-1\n"
            "    provider: imap_hostgator\n"
            "    address: alex@example.com\n"
            "    imap:\n"
            "      port: 993\n"
            "      ssl: true\n"
            "    smtp_enabled_v1: false\n"
            "    read_only: true\n"
        ),
    )
    registry = AccountRegistry.load(yaml_path, env={})
    entry = registry.entries[0]
    assert entry.imap is not None
    assert entry.imap.port == 993
    assert entry.imap.ssl is True
    assert entry.imap.smtp_enabled_v1 is False
