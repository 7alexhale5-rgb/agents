"""Stub dataclasses + ABCs from SPEC.md.

Replaced by real modules in sub-phase 4.7.1+. This file exists so:
1. `tests/spec_self_consistency.py` can verify SPEC.md contracts compile
2. ruff + mypy can lint the type surface end-to-end before runtime code lands
"""
from __future__ import annotations

import abc
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

# ----- config dataclasses -----

@dataclass(frozen=True)
class Manifest:
    tier: str
    channels: list[str]
    model_routing: dict[str, str]
    memory_axes: list[str]
    guardrails: list[str]
    sla: dict[str, float]


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
    soul: str
    user: str
    memory: str
    claude: str
    manifest: Manifest
    config: Config
    a2a_card: A2ACard
    pricing: Pricing


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
    in_reply_to: str | None = None
    message_id: str = ""


# ----- runtime types -----

@dataclass
class MutationProposal:
    proposal_id: str
    operation: str
    table: str
    rows_affected: list[dict[str, Any]]
    rationale: str


@dataclass
class ToolContext:
    profile_slug: str
    session_id: str
    langfuse_trace_id: str
    mutation_proposal_callback: Callable[[MutationProposal], Awaitable[str]]


@dataclass
class ToolResult:
    ok: bool
    output: Any
    error: str | None = None
    cost_usd: Decimal = Decimal("0")


@dataclass
class SessionResult:
    session_id: str
    final_message: Message
    steps_taken: int
    cost_usd: Decimal
    finish_reason: str  # "stop" | "max_steps" | "cost_ceiling" | "interrupt"


# ----- ABCs -----

class Tool(abc.ABC):
    name: str
    description: str
    parameters: dict[str, Any]

    @abc.abstractmethod
    async def invoke(self, args: dict[str, Any], context: ToolContext) -> ToolResult:
        ...


class ChannelHealth:
    def __init__(self, ok: bool, details: dict[str, Any] | None = None) -> None:
        self.ok = ok
        self.details = details or {}


class ChannelError(Exception):
    pass


class ChannelConnectError(ChannelError):
    pass


class ChannelAuthError(ChannelError):
    pass


class ChannelRateLimited(ChannelError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"rate limited; retry after {retry_after_seconds}s")
        self.retry_after_seconds = retry_after_seconds


class ChannelMessageTooLarge(ChannelError):
    pass


class Channel(abc.ABC):
    name: str
    profile_slug: str

    @abc.abstractmethod
    async def connect(self) -> None: ...

    @abc.abstractmethod
    async def receive(self) -> AsyncIterator[InboundMessage]: ...

    @abc.abstractmethod
    async def send(self, msg: OutboundMessage) -> None: ...

    @abc.abstractmethod
    async def typing(self, target_user_id: str, on: bool) -> None: ...

    @abc.abstractmethod
    async def ack(self, message_id: str) -> None: ...

    @abc.abstractmethod
    async def disconnect(self) -> None: ...

    async def health(self) -> ChannelHealth:
        return ChannelHealth(ok=False)
