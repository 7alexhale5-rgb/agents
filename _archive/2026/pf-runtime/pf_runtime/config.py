"""Profile configuration dataclasses and loader.

Promoted from stubs/spec_stubs.py + extended with load_profile().
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any

# ----- supporting dataclasses -----

@dataclass(frozen=True)
class MCPServerSpec:
    name: str
    url: str
    version: str


@dataclass(frozen=True)
class ChannelSpec:
    name: str
    enabled: bool
    config: dict[str, Any]


@dataclass(frozen=True)
class Manifest:
    tier: str
    channels: list[str]
    model_routing: dict[str, str]
    memory_axes: list[str]
    guardrails: list[str]
    sla: dict[str, float]


@dataclass(frozen=True)
class Config:
    mcp_servers: list[MCPServerSpec]
    channels: dict[str, ChannelSpec]
    memory_provider: str
    skill_gen_autonomy: str


@dataclass(frozen=True)
class A2ACard:
    schema_version: str
    capabilities: list[dict[str, Any]]
    endpoint: str


@dataclass(frozen=True)
class Pricing:
    tier: str
    monthly_usd: Decimal
    daily_cap_usd: Decimal


@dataclass(frozen=True)
class Profile:
    slug: str
    model: str
    provider: str
    soul_md_path: Path
    user_md_path: Path
    memory_md_path: Path
    env_path: Path


# ----- message types -----

@dataclass
class Attachment:
    kind: str
    data: bytes | str
    content_type: str


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    tool_call_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class InboundMessage:
    channel: str
    profile_slug: str
    user_id: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    message_id: str = ""


@dataclass(frozen=True)
class OutboundMessage:
    channel: str
    profile_slug: str
    target_user_id: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    in_reply_to: str | None = None
    message_id: str = ""


# ----- profile loader -----

def _parse_yaml_key(text: str, key: str) -> str:
    """Minimal YAML scalar extractor — handles `key: value` lines.

    Only used for the two keys we need from config.yaml (model.default,
    model.provider). We avoid importing PyYAML to stay dep-free in the
    throwaway loop. This is NOT a general YAML parser.
    """
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*:\s*(.+)$", re.MULTILINE)
    m = pattern.search(text)
    if not m:
        raise ValueError(f"Key '{key}' not found in config.yaml")
    return m.group(1).strip().strip('"').strip("'")


def load_profile(
    slug: str,
    *,
    hermes_home: Path | None = None,
) -> Profile:
    """Load a Profile from a Hermes profile directory.

    Reads ``hermes_home / "profiles" / slug / config.yaml``.
    Returns a Profile with path references to SOUL.md, USER.md,
    MEMORY.md, and .env — none of these large files are read at
    load time; the runtime reads them on demand.

    Raises:
        FileNotFoundError: if the profile directory or config.yaml
            does not exist.
        ValueError: if required keys (model.default, model.provider)
            are missing from config.yaml.
    """
    if hermes_home is None:
        hermes_home = Path.home() / ".hermes"
    profile_dir = hermes_home / "profiles" / slug
    config_path = profile_dir / "config.yaml"

    if not profile_dir.is_dir():
        raise FileNotFoundError(f"Profile directory not found: {profile_dir}")
    if not config_path.is_file():
        raise FileNotFoundError(f"config.yaml not found: {config_path}")

    config_text = config_path.read_text(encoding="utf-8")

    # config.yaml uses `model.default` and `model.provider` (NOT
    # `default_model`/`default_provider` — confirmed in config.yaml comment
    # and auxiliary_client.py:1305-1342).
    model = _parse_yaml_key(config_text, "default")
    provider = _parse_yaml_key(config_text, "provider")

    soul_md_path = profile_dir / "SOUL.md"
    user_md_path = profile_dir / "USER.md"
    memory_md_path = profile_dir / "MEMORY.md"
    env_path = profile_dir / ".env"

    for path, label in [
        (soul_md_path, "SOUL.md"),
        (user_md_path, "USER.md"),
        (env_path, ".env"),
    ]:
        if not path.is_file():
            raise FileNotFoundError(f"{label} not found: {path}")

    return Profile(
        slug=slug,
        model=model,
        provider=provider,
        soul_md_path=soul_md_path,
        user_md_path=user_md_path,
        memory_md_path=memory_md_path,
        env_path=env_path,
    )
