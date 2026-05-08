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

Sub-phase communications additions:
  - Schema-validated JSON tool calls
  - Multi-step loop bounded by max_steps
  - Cost ceiling + timeout enforcement
  - Tool-call trace lines
"""
from __future__ import annotations

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from pf_runtime.config import InboundMessage, Message, Profile
from pf_runtime.runtime.model_adapter import ModelAdapter
from pf_runtime.runtime.tool_dispatch import Tool, ToolContext, ToolDispatcher
from pf_runtime.runtime.trace import emit_session_trace

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
    tools: list[Tool] | None = None,
    interrupt: asyncio.Event | None = None,
    memory: MemoryStack | None = None,
) -> SessionResult:
    """Run a single agent session end-to-end.

    Sub-phase A/B plus communications tool-loop implementation:
      1. Build system prompt — from MemoryStack (Tier 1) when available,
         otherwise reads SOUL.md + USER.md directly from profile paths.
      2. Hydrate conversation with last-N buffer messages (Tier 2) when
         memory is wired.
      3. Send user message to LLM.
      4. Dispatch schema-valid tool calls when the model returns a JSON
         ``{"tool_call": ...}`` envelope.
      5. Persist user + final assistant message to Tier 2 buffer.

    Args:
        profile: The loaded Profile (contains paths to SOUL.md, USER.md, etc.)
        inbound: The inbound message from the user
        model_adapter: The LLM adapter to use for completion
        max_steps: Maximum number of model/tool turns.
        cost_ceiling_usd: Cost ceiling enforced after model/tool calls.
        tools: Optional schema-validated tool list.
        interrupt: Asyncio Event for cancellation checked before each step.
        memory: Optional MemoryStack; when provided, Tier 1 context + Tier 2
            buffer hydration are active and each turn is persisted.

    Returns:
        SessionResult with the assistant reply
    """
    t0 = time.perf_counter()
    session_id = str(uuid.uuid4())
    # Step 1: Build system prompt
    if memory is not None:
        # Tier 1: soul context (mtime-cached, 30s TTL)
        tier1_context = memory.system_prompt(profile)
        skill_block = memory.skills_context_for_prompt(profile)
        if skill_block:
            system_prompt = (
                f"{tier1_context}\n\n{skill_block}\n\n"
                "Respond in complete sentences. Never give one-word answers."
            )
        else:
            system_prompt = (
                f"{tier1_context}\n\n"
                "Respond in complete sentences. Never give one-word answers."
            )

        if memory.episodic is not None:
            q = inbound.text[:2000]
            hits = await memory.episodic.query(q, profile.slug)
            if hits:
                block = "\n# EPISODIC SNIPPETS\n" + "\n".join(
                    f"- {h[:500]}" for h in hits[:8]
                )
                system_prompt = f"{system_prompt}{block}"
    else:
        # Fallback: direct file reads (sub-phase A path, no memory wired)
        soul_content = profile.soul_md_path.read_text(encoding="utf-8")
        user_content = profile.user_md_path.read_text(encoding="utf-8")
        system_prompt = (
            f"# SOUL\n\n{soul_content.strip()}\n\n"
            f"# USER PROFILE\n\n{user_content.strip()}\n\n"
            "Respond in complete sentences. Never give one-word answers."
        )

    dispatcher = ToolDispatcher(tools or [])
    tool_catalog = dispatcher.prompt_catalog()
    if tool_catalog:
        system_prompt = f"{system_prompt}\n\n{tool_catalog}"

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

    cost_usd = Decimal("0")
    assistant_content = ""
    finish_reason = "stop"
    steps_taken = 0
    context = ToolContext(profile_slug=profile.slug, session_id=session_id)

    for step in range(max_steps):
        steps_taken = step + 1
        if interrupt is not None and interrupt.is_set():
            finish_reason = "interrupt"
            break

        assistant_content, call_cost = await asyncio.wait_for(
            model_adapter.complete(messages, model=profile.model, max_tokens=1024),
            timeout=90,
        )
        cost_usd += call_cost
        if cost_usd > cost_ceiling_usd:
            finish_reason = "cost_ceiling"
            break

        tool_call = _extract_tool_call(assistant_content)
        if tool_call is None:
            if len(assistant_content.strip()) < 10:
                retry_messages: list[dict[str, str]] = [
                    *messages,
                    {"role": "assistant", "content": assistant_content},
                    {"role": "user", "content": "Please give a complete sentence answer."},
                ]
                retry_content, retry_cost = await asyncio.wait_for(
                    model_adapter.complete(
                        retry_messages,
                        model=profile.model,
                        max_tokens=1024,
                    ),
                    timeout=90,
                )
                assistant_content = retry_content
                cost_usd += retry_cost
                if cost_usd > cost_ceiling_usd:
                    finish_reason = "cost_ceiling"
            break

        tool_result = await asyncio.wait_for(
            dispatcher.dispatch(tool_call["name"], tool_call["arguments"], context),
            timeout=60,
        )
        cost_usd += tool_result.cost_usd
        if cost_usd > cost_ceiling_usd:
            finish_reason = "cost_ceiling"
            break
        messages.append({"role": "assistant", "content": assistant_content})
        messages.append(
            {
                "role": "tool",
                "content": json.dumps(
                    {
                        "name": tool_call["name"],
                        "ok": tool_result.ok,
                        "output": tool_result.output,
                        "error": tool_result.error,
                    },
                    default=str,
                    sort_keys=True,
                ),
            }
        )
    else:
        finish_reason = "max_steps"

    # Step 4: Build typed message objects for the result
    user_message = Message(role="user", content=inbound.text)
    assistant_message = Message(role="assistant", content=assistant_content)

    # Step 5: Persist to Tier 2 buffer so the next session sees this turn
    if memory is not None:
        memory.append(profile, user_message)
        memory.append(profile, assistant_message)

    result_messages = [user_message, assistant_message]

    latency_ms = (time.perf_counter() - t0) * 1000
    emit_session_trace(
        profile_slug=profile.slug,
        session_id=session_id,
        model=profile.model,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        cost_usd=cost_usd,
    )

    return SessionResult(
        messages=result_messages,
        steps=steps_taken,
        finish_reason=finish_reason,
        cost_usd=cost_usd,
        session_id=session_id,
    )


def _extract_tool_call(content: str) -> dict[str, Any] | None:
    """Parse the narrow PF Runtime JSON tool-call envelope."""
    text = content.strip()
    if not text.startswith("{"):
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    call = payload.get("tool_call") if isinstance(payload, dict) else None
    if not isinstance(call, dict):
        return None
    name = call.get("name")
    arguments = call.get("arguments")
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return None
    return {"name": name, "arguments": arguments}
