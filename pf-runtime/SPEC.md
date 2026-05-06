# PrettyFly Runtime — surface contract

> **Status:** v0.1 spec, locked 2026-05-06. All sub-phase 4.7.x builds against this. Changes require Codex review + ADR amendment.

## Goal

Define the public API surface of PF Runtime such that:

1. **Profile dirs are runtime-portable** — Hermes today, PF Runtime tomorrow, both load `~/Projects/agents/hermes/profiles/{slug}/` without modification.
2. **Channel adapters are drop-in replaceable** — Slack, Telegram, Email, Discord plug into the same ABC.
3. **Memory tiers compose explicitly** — read-through cache ordering is contractual, not emergent.
4. **Tool dispatch is MCP-native** — every tool is reachable via MCP; native Python tools wrap the MCP protocol.

## Module layout

> **Note on paths vs Python imports:** the paths below are filesystem paths relative to the repo root (`~/Projects/agents/`), and the tree root is the kebab-cased project directory `pf-runtime/`. The actual Python package is the snake-cased `pf_runtime/` (one level deeper, configured by `pyproject.toml`). Test invocations therefore set `PYTHONPATH=pf-runtime` and the Python imports are `from pf_runtime.runtime.loop import run_session`, never `from pf-runtime...` (which is illegal). The kebab/snake split lets the project directory match Alex's filesystem protocol while the package follows PEP 8.

```
pf-runtime/                  # project root (kebab-case per filesystem protocol)
└── pf_runtime/              # Python package (snake_case per PEP 8) — what `import` sees
    ├── __init__.py             # version, package metadata
    ├── __main__.py             # CLI: `python -m pf_runtime <command>`
    ├── config.py               # Profile, Manifest, Config, A2ACard, Pricing dataclasses
    ├── runtime/
    │   ├── loop.py             # async def run_session(...)
    │   ├── model_adapter.py    # LiteLLMAdapter
    │   ├── tool_dispatch.py    # ToolDispatcher
    │   ├── stop_condition.py   # StopCondition
    │   └── audit.py            # AuditSink (Langfuse + SQLite mutation_audit)
    ├── memory/
    │   ├── tier1_soul.py       # SoulReader (read-only, mtime watch)
    │   ├── tier2_buffer.py     # BufferStore (SQLite WAL, per-profile)
    │   ├── tier3_episodic.py   # EpisodicClient (LAIK MCP)
    │   └── tier4_skills.py     # SkillRegistry (agentskills.io progressive disclosure)
    ├── skill_gen/
    │   ├── self_author.py      # SkillAuthor
    │   └── approver.py         # SkillApprover (operator-gated for non-personal profiles)
    ├── dream/
    │   ├── post_session.py     # DreamLoop
    │   └── bounds_audit.py     # BoundsAuditor (SKILL_SELF_GEN_BOUNDS.md enforcement)
    ├── channels/
    │   ├── adapter_base.py     # Channel ABC (per ADAPTER_PLUGIN_INTERFACE.md)
    │   ├── slack.py            # SlackChannel
    │   ├── telegram.py         # TelegramChannel
    │   ├── email.py            # EmailChannel
    │   ├── discord.py          # DiscordChannel
    │   └── keychain.py         # macOS Keychain bridge
    └── kanban/
        ├── schema.sql          # Postgres tables (pf_kanban_tasks, pf_kanban_transitions, pf_kanban_audit)
        ├── store.py            # asyncpg-backed KanbanStore
        ├── api.py              # FastAPI: REST + WebSocket
        └── worker.py           # KanbanWorker
```

## Core dataclasses

```python
# pf-runtime/config.py

@dataclass(frozen=True)
class Profile:
    slug: str
    soul: str           # SOUL.md content (frozen at load)
    user: str           # USER.md content
    memory: str         # MEMORY.md content (mutable via dream loop)
    claude: str         # CLAUDE.md (Layer-2 routing)
    manifest: Manifest
    config: Config
    a2a_card: A2ACard
    pricing: Pricing

@dataclass(frozen=True)
class Manifest:
    tier: str           # "lite" | "pro" | "scale"
    channels: list[str]
    model_routing: dict[str, str]
    memory_axes: list[str]
    guardrails: list[str]
    sla: dict[str, float]

@dataclass(frozen=True)
class Config:
    mcp_servers: list[MCPServerSpec]
    channels: dict[str, ChannelSpec]
    memory_provider: str  # "builtin" | "honcho"
    skill_gen_autonomy: str  # "auto" | "approve" | "disabled"

@dataclass
class Message:
    role: str           # "user" | "assistant" | "tool" | "system"
    content: str
    tool_call_id: str | None = None
    metadata: dict | None = None

@dataclass
class InboundMessage:
    channel: str
    profile_slug: str
    user_id: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    message_id: str = ""  # idempotency key (UUIDv7 by default)

@dataclass
class OutboundMessage:
    channel: str
    profile_slug: str
    target_user_id: str
    text: str
    attachments: list[Attachment] = field(default_factory=list)
    in_reply_to: str | None = None
    message_id: str = ""  # for idempotency on reconnect

@dataclass
class ToolContext:
    profile_slug: str
    session_id: str
    langfuse_trace_id: str
    mutation_proposal_callback: Callable[[MutationProposal], Awaitable[str]]
```

## Loop primitive (the thing Hermes hides)

```python
# pf-runtime/runtime/loop.py

async def run_session(
    profile: Profile,
    inbound: InboundMessage,
    *,
    channel: Channel,
    tools: list[Tool],
    memory: MemoryStack,
    audit: AuditSink,
    max_steps: int = 8,
    cost_ceiling_usd: Decimal = Decimal("0.50"),
    interrupt: asyncio.Event | None = None,
) -> SessionResult:
    """One agent session, end-to-end. Loop terminates on:
      - finish_reason='stop' from LLM (normal completion)
      - step count >= max_steps
      - cost_so_far >= cost_ceiling_usd
      - interrupt event set
    Every step writes to AuditSink (Langfuse trace + SQLite mutation_audit row).
    """
```

## Channel ABC

```python
# pf-runtime/channels/adapter_base.py

class Channel(abc.ABC):
    @abc.abstractmethod
    async def connect(self) -> None: ...
    @abc.abstractmethod
    async def receive(self) -> AsyncIterator[InboundMessage]: ...
    @abc.abstractmethod
    async def send(self, msg: OutboundMessage) -> None: ...
    @abc.abstractmethod
    async def typing(self, profile_slug: str, target: str, on: bool) -> None: ...
    @abc.abstractmethod
    async def ack(self, message_id: str) -> None: ...
    @abc.abstractmethod
    async def disconnect(self) -> None: ...

    # Idempotency contract: outbound `send` is no-op if `msg.message_id` was already sent.
    # Reconnect contract: `connect` is idempotent; runtime calls it once at startup and again on `ChannelError`.
```

## Tool ABC

```python
# pf-runtime/runtime/tool_dispatch.py

class Tool(abc.ABC):
    name: str            # MCP tool name, namespace.action format
    description: str
    parameters: dict     # JSONSchema (Draft 2020-12)

    @abc.abstractmethod
    async def invoke(self, args: dict, context: ToolContext) -> ToolResult: ...

class ToolResult(BaseModel):
    ok: bool
    output: Any
    error: str | None = None
    cost_usd: Decimal = Decimal("0")
```

**Argument validation contract.** `ToolDispatcher.dispatch(name, args, context)` MUST validate `args` against the tool's `parameters` JSONSchema _before_ calling `invoke()`. Validation failure raises `ToolValidationError(name, schema_path, message)` and is recorded in `audit.tool_validation_failures`; `invoke()` is never reached. This keeps tool implementations free of defensive arg-shape checks and centralizes the failure mode. JSONSchema is Draft 2020-12 via `jsonschema>=4.21`; format checkers (`uuid`, `date-time`, `email`, `uri`) are enabled by default. Schemas are loaded once per Tool registration and cached.

## Memory stack

```python
# pf-runtime/memory/__init__.py

class MemoryStack:
    """Composes the four tiers per MEMORY_LIFECYCLE.md.
    Read order: SOUL.md → SQLite buffer → LAIK MCP episodic → skills (fall-through).
    Write order: tier 2 sync; tier 3 async (30s flush); tier 4 sync after operator approval.
    """
    def __init__(
        self,
        soul: SoulReader,
        buffer: BufferStore,
        episodic: EpisodicClient,
        skills: SkillRegistry,
    ): ...

    async def read(self, profile_slug: str, session_id: str) -> list[Message]: ...
    async def append(self, profile_slug: str, session_id: str, msg: Message) -> None: ...
    async def flush(self, profile_slug: str) -> None: ...  # forces tier-3 batch flush
```

## CLI surface

```bash
# Daemon mode — runs all profiles' channels + Kanban worker
pf-runtime run --all-profiles

# Single profile mode
pf-runtime run --profile personal

# Kanban worker spawn (called by api.py on task claim)
pf-runtime kanban-worker --task-id <uuid>

# Health probe
pf-runtime healthcheck --all-profiles

# Shadow mode — read-only mirror of Hermes traffic
pf-runtime shadow --profile personal --mirror-from hermes

# State management
pf-runtime symlink-state --to <path>     # cutover-time profile dir flip
```

## Test surface (every module ships with a test sibling)

```
tests/
├── spec_self_consistency.py       # asserts every contract has a stub implementation
├── profile_dir_contract.py        # nightly: 13 profiles loadable by Hermes + PF Runtime
├── golden_set_regression.py       # 30-question golden set, token delta vs Hermes baseline
├── memory_consistency_test.py     # concurrent skill-gen + dream-loop, 100-message corpus
├── skill_gen_bounds_test.py       # SKILL_SELF_GEN_BOUNDS.md enforcement
├── channel_abc_test.py            # adapter chaos test, idempotency check
├── slack_parity.py                # 50-message parity test on atlas-ceo shadow workspace
├── kanban_load_test.py            # 13 profiles × 100 concurrent task writes
└── laik_mcp_contract.py           # LAIK MCP surface contract
```

## Versioning + reversibility

- v0.1 = pre-greenlight stub. Changes are free.
- v0.x = sub-phase 4.7.x deliverables. Changes require Codex review.
- v1.0 = post-cutover. Changes require ADR amendment + 14-day shadow re-validation.
