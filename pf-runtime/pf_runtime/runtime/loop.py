"""Session loop — the core agent turn primitive.

Sub-phase A (throwaway): single-step loop only.
  - Reads SOUL.md + USER.md from the profile paths (no mtime cache yet)
  - Prepends them as a system prompt
  - Sends the inbound user message
  - Returns the assistant reply in a SessionResult

Sub-phase B additions (wired here):
  - memory: MemoryStack | None parameter accepted by run_session()
  - When memory is not None:
      - system_prompt is prefixed with Tier 1 soul context
      - last-N buffer messages are prepended to the conversation
      - user + assistant messages are appended to the buffer after each turn

Deferred to sub-phase A full:
  - Tool dispatch (tools=[] stub parameter accepted but ignored)
  - Multi-step loop (max_steps is accepted but loop exits after step 1)
  - Cost ceiling enforcement (ceiling is recorded in result, not enforced)
  - Langfuse trace export (stdout only for now)
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pf_runtime.config import InboundMessage, Message, Profile
from pf_runtime.runtime.model_adapter import ModelAdapter

if TYPE_CHECKING:
    from pf_runtime.memory import MemoryStack


@dataclass
class SessionResult:
    """Result of a single agent session."""

    messages: list[Message]
    steps: int
    finish_reason: str  # "stop" | "max_steps" | "cost_ceiling" | "interrupt"
    cost_usd: Decimal
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))


async def run_session(
    profile: Profile,
    inbound: InboundMessage,
    *,
    model_adapter: ModelAdapter,
    max_steps: int = 4,
    cost_ceiling_usd: Decimal = Decimal("0.50"),
    tools: list[Any] | None = None,
    interrupt: asyncio.Event | None = None,
    memory: MemoryStack | None = None,
) -> SessionResult:
    """Run a single agent session end-to-end.

    Sub-phase A (throwaway) + sub-phase B (memory stack) implementation:
      1. Build system prompt — from MemoryStack (Tier 1) when available,
         otherwise reads SOUL.md + USER.md directly from profile paths.
      2. Hydrate conversation with last-N buffer messages (Tier 2) when
         memory is wired.
      3. Send user message to LLM.
      4. Persist user + assistant messages to Tier 2 buffer.
      5. Return SessionResult with the assistant reply.

    Args:
        profile: The loaded Profile (contains paths to SOUL.md, USER.md, etc.)
        inbound: The inbound message from the user
        model_adapter: The LLM adapter to use for completion
        max_steps: Maximum number of tool-call steps (throwaway: exits after 1)
        cost_ceiling_usd: Cost ceiling (throwaway: recorded but not enforced)
        tools: Tool list stub — accepted but ignored in throwaway
        interrupt: Asyncio Event for cancellation (throwaway: not checked)
        memory: Optional MemoryStack; when provided, Tier 1 context + Tier 2
            buffer hydration are active and each turn is persisted.

    Returns:
        SessionResult with the assistant reply
    """
    # Step 1: Build system prompt
    if memory is not None:
        # Tier 1: soul context (mtime-cached, 30s TTL)
        tier1_context = memory.system_prompt(profile)
        system_prompt = (
            f"{tier1_context}\n\n"
            "Respond in complete sentences. Never give one-word answers."
        )
    else:
        # Fallback: direct file reads (sub-phase A path, no memory wired)
        soul_content = profile.soul_md_path.read_text(encoding="utf-8")
        user_content = profile.user_md_path.read_text(encoding="utf-8")
        system_prompt = (
            f"# SOUL\n\n{soul_content.strip()}\n\n"
            f"# USER PROFILE\n\n{user_content.strip()}\n\n"
            "Respond in complete sentences. Never give one-word answers."
        )

    # Step 2: Assemble messages — seed with system prompt
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
    ]

    # Tier 2: hydrate with recent buffer messages (most-recent-first → reverse
    # to chronological order for LLM context)
    if memory is not None:
        prior = memory.recent_messages(profile, limit=10)
        # prior is DESC; reverse to chronological before injecting
        for msg in reversed(prior):
            messages.append({"role": msg.role, "content": msg.content})

    # Append the current user turn
    messages.append({"role": "user", "content": inbound.text})

    # Step 3: Call the LLM (with one retry if response is too short)
    assistant_content, cost_usd = await model_adapter.complete(
        messages,
        model=profile.model,
        max_tokens=1024,
    )

    # If model gives a very short response (< 10 chars), retry once with an
    # explicit verbosity nudge appended to the conversation. Small free-tier
    # models (e.g. nemotron-nano:free) are stochastically terse on simple
    # queries; a second turn requesting elaboration reliably produces a full
    # sentence. This is a throwaway-only behavior; sub-phase A full will
    # use a warm-start system prompt instead.
    if len(assistant_content.strip()) < 10:
        retry_messages: list[dict[str, str]] = [
            *messages,
            {"role": "assistant", "content": assistant_content},
            {
                "role": "user",
                "content": "Please give a complete sentence answer.",
            },
        ]
        retry_content, retry_cost = await model_adapter.complete(
            retry_messages,
            model=profile.model,
            max_tokens=1024,
        )
        assistant_content = retry_content
        cost_usd = cost_usd + retry_cost

    # Step 4: Build typed message objects for the result
    user_message = Message(role="user", content=inbound.text)
    assistant_message = Message(role="assistant", content=assistant_content)

    # Step 5: Persist to Tier 2 buffer so the next session sees this turn
    if memory is not None:
        memory.append(profile, user_message)
        memory.append(profile, assistant_message)

    result_messages = [user_message, assistant_message]

    return SessionResult(
        messages=result_messages,
        steps=1,
        finish_reason="stop",
        cost_usd=cost_usd,
    )
