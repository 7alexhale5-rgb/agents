"""Sentry optional init from profile .env."""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from pf_runtime.config import Profile
from pf_runtime.runtime import sentry_init as sentry_init_mod
from pf_runtime.runtime.sentry_init import init_sentry_from_profile


def _minimal_profile(tmp: Path, env_lines: str) -> Profile:
    pdir = tmp / "profiles" / "personal"
    pdir.mkdir(parents=True)
    (pdir / "config.yaml").write_text(
        "default: x/y\nprovider: openrouter\n",
        encoding="utf-8",
    )
    (pdir / "SOUL.md").write_text("# s", encoding="utf-8")
    (pdir / "USER.md").write_text("# u", encoding="utf-8")
    (pdir / "MEMORY.md").write_text("", encoding="utf-8")
    (pdir / ".env").write_text(env_lines, encoding="utf-8")
    return Profile(
        slug="personal",
        model="x/y",
        provider="openrouter",
        soul_md_path=pdir / "SOUL.md",
        user_md_path=pdir / "USER.md",
        memory_md_path=pdir / "MEMORY.md",
        env_path=pdir / ".env",
    )


def test_no_dsn_does_not_init(tmp_path: Path) -> None:
    sentry_init_mod.reset_sentry_init_for_tests()
    profile = _minimal_profile(tmp_path, "FOO=bar\n")
    init_sentry_from_profile(profile, component="gateway")
    assert not sentry_init_mod.sentry_initialized()


def test_dsn_triggers_init(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    sentry_init_mod.reset_sentry_init_for_tests()
    calls: list[dict] = []

    def fake_init(**kwargs: object) -> None:
        calls.append(dict(kwargs))

    fake_sdk = types.ModuleType("sentry_sdk")
    fake_sdk.init = fake_init
    fake_sdk.set_tag = lambda *_a, **_k: None
    monkeypatch.setitem(sys.modules, "sentry_sdk", fake_sdk)

    profile = _minimal_profile(tmp_path, "SENTRY_DSN=https://key@o.ingest.sentry.io/1\n")
    init_sentry_from_profile(profile, component="cli")
    assert len(calls) == 1
    assert calls[0].get("dsn") == "https://key@o.ingest.sentry.io/1"

    init_sentry_from_profile(profile, component="cli")
    assert len(calls) == 1, "second call should be no-op"
