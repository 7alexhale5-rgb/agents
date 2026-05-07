"""Session loop — the core agent turn primitive.

Sub-phase A (throwaway): single-step loop only.
  - Reads SOUL.md + USER.md from the profile paths (no mtime cache yet)
  - Prepends them as a system prompt
  - Sends the inbound user message
  - Returns the assistant reply in a SessionResult

Deferred to sub-phase A full:
  - Tool dispatch (tools=[] stub parameter accepted but ignored)
  - Multi-step loop (max_steps is accepted but loop exits after step 1)
  - Cost ceiling enforcement (ceiling is recorded in result, not enforced)
  - Langfuse trace export (stdout only for now)
  - Memory tier integration beyond reading SOUL/USER
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from pf_runtime.config import InboundMessage, Message, Profile
from pf_runtime.runtime.model_adapter import ModelAdapter


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
) -> SessionResult:
    """Run a single agent session end-to-end.

    Sub-phase A (throwaway) implementation:
      1. Read SOUL.md + USER.md from profile paths
      2. Build system prompt from concatenated content
      3. Send user message to LLM
      4. Return SessionResult with the assistant reply

    Args:
        profile: The loaded Profile (contains paths to SOUL.md, USER.md, etc.)
        inbound: The inbound message from the user
        model_adapter: The LLM adapter to use for completion
        max_steps: Maximum number of tool-call steps (throwaway: exits after 1)
        cost_ceiling_usd: Cost ceiling (throwaway: recorded but not enforced)
        tools: Tool list stub — accepted but ignored in throwaway
        interrupt: Asyncio Event for cancellation (throwaway: not checked)

    Returns:
        SessionResult with the assistant reply
    """
    # Step 1: Build system prompt from SOUL.md + USER.md
    soul_content = profile.soul_md_path.read_text(encoding="utf-8")
    user_content = profile.user_md_path.read_text(encoding="utf-8")

    system_prompt = (
        f"# SOUL\n\n{soul_content.strip()}\n\n"
        f"# USER PROFILE\n\n{user_content.strip()}\n\n"
        "Respond in complete sentences. Never give one-word answers."
    )

    # Step 2: Assemble messages
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": inbound.text},
    ]

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

    # Step 4: Build result
    result_messages = [
        Message(role="user", content=inbound.text),
        Message(role="assistant", content=assistant_content),
    ]

    return SessionResult(
        messages=result_messages,
        steps=1,
        finish_reason="stop",
        cost_usd=cost_usd,
    )
