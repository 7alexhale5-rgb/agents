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
import re
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pf_runtime.config import InboundMessage, Message, Profile
from pf_runtime.runtime.model_adapter import ModelAdapter
from pf_runtime.runtime.tool_dispatch import Tool, ToolContext, ToolDispatcher, ToolResult
from pf_runtime.runtime.trace import emit_session_trace

if TYPE_CHECKING:
    from pf_runtime.memory import MemoryStack


@dataclass
class SessionResult:
    """Result of a single agent session."""

    messages: list[Message]
    steps: int
    finish_reason: str  # "stop" | "max_steps" | "cost_ceiling" | "interrupt" | "model_error"
    cost_usd: Decimal
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)


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
    completion_model = _select_completion_model(profile, inbound.text)

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
    tool_was_used = False
    proposal_tool_attempted = False
    follow_up_tool_attempted = False
    verified_action_receipts: list[dict[str, Any]] = []
    verified_follow_up_receipts: list[dict[str, Any]] = []
    follow_up_brief_fields: dict[str, str] | None = None

    atlas_capability = _atlas_capability_for(profile, inbound.text)
    source_tool = _source_tool_for_capability(atlas_capability, dispatcher.tool_names)
    if source_tool is not None:
        tool_result = await _safe_dispatch(
            dispatcher,
            source_tool,
            {"profile_limit": 20, "period_days": 7},
            context,
        )
        tool_was_used = True
        cost_usd += tool_result.cost_usd
        source_output = tool_result.output
        if not tool_result.ok:
            source_output = _degraded_source_packet(source_tool, tool_result.error)
        source_label = "Verified" if tool_result.ok else "Degraded"
        messages.append(
            {
                "role": "user",
                "content": (
                    f"{source_label} source packet from {source_tool}. Use this packet; "
                    "do not call profile skills as tools. Cite source names and "
                    "name missing signals separately.\n\n"
                    f"{json.dumps(source_output, default=str, sort_keys=True)}"
                ),
            }
        )
        proposal_instruction = _atlas_action_proposal_instruction(
            atlas_capability,
            dispatcher.tool_names,
        )
        if proposal_instruction:
            messages.append({"role": "user", "content": proposal_instruction})
        follow_up_instruction = _atlas_follow_up_instruction(
            atlas_capability,
            dispatcher.tool_names,
        )
        if follow_up_instruction:
            messages.append({"role": "user", "content": follow_up_instruction})
        brief_instruction = _atlas_brief_structure_instruction(atlas_capability)
        if brief_instruction:
            messages.append({"role": "user", "content": brief_instruction})

    for step in range(max_steps):
        steps_taken = step + 1
        if interrupt is not None and interrupt.is_set():
            finish_reason = "interrupt"
            break

        try:
            assistant_content, call_cost = await asyncio.wait_for(
                model_adapter.complete(messages, model=completion_model, max_tokens=1024),
                timeout=90,
            )
        except Exception as exc:
            assistant_content = _model_error_message(profile, completion_model, exc)
            finish_reason = "model_error"
            break
        cost_usd += call_cost
        if cost_usd > cost_ceiling_usd:
            finish_reason = "cost_ceiling"
            break

        tool_call = _extract_tool_call(assistant_content)
        if tool_call is None:
            if _needs_atlas_proposal_tool_retry(
                atlas_capability,
                dispatcher.tool_names,
                proposal_tool_attempted,
                verified_action_receipts,
            ):
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You have not called `atlas.propose_action` yet. To create "
                            "the requested approval proposal, reply only with the JSON "
                            "`tool_call` envelope for `atlas.propose_action` using the "
                            "verified source packet. If you cannot create it, say why "
                            "after the tool attempt fails."
                        ),
                    }
                )
                continue
            if _needs_atlas_follow_up_tool_retry(
                atlas_capability,
                dispatcher.tool_names,
                follow_up_tool_attempted,
                verified_follow_up_receipts,
            ):
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You have not called `atlas.record_follow_up` yet. To "
                            "record the approved-decision follow-up, reply only with "
                            "the JSON `tool_call` envelope for "
                            "`atlas.record_follow_up` using the verified source "
                            "packet. If a ready follow-up already exists for this "
                            "source action, say that instead and do not claim a new "
                            "event was recorded."
                        ),
                    }
                )
                continue
            if len(assistant_content.strip()) < 10:
                retry_messages: list[dict[str, str]] = [
                    *messages,
                    {"role": "assistant", "content": assistant_content},
                    {"role": "user", "content": "Please give a complete sentence answer."},
                ]
                try:
                    retry_content, retry_cost = await asyncio.wait_for(
                        model_adapter.complete(
                            retry_messages,
                            model=completion_model,
                            max_tokens=1024,
                        ),
                        timeout=90,
                    )
                except Exception as exc:
                    assistant_content = _model_error_message(profile, completion_model, exc)
                    finish_reason = "model_error"
                    break
                assistant_content = retry_content
                cost_usd += retry_cost
                if cost_usd > cost_ceiling_usd:
                    finish_reason = "cost_ceiling"
            break

        tool_args = dict(tool_call["arguments"])
        if tool_call["name"] == "atlas.propose_action":
            tool_args.update(_atlas_model_route_metadata(completion_model, assistant_content))

        tool_result = await _safe_dispatch(
            dispatcher,
            tool_call["name"],
            tool_args,
            context,
        )
        tool_was_used = True
        if tool_call["name"] == "atlas.propose_action":
            proposal_tool_attempted = True
            if tool_result.ok:
                receipt = _verified_action_receipt(tool_result.output)
                if receipt is not None:
                    verified_action_receipts.append(receipt)
        if tool_call["name"] == "atlas.record_follow_up":
            follow_up_tool_attempted = True
            if tool_result.ok:
                receipt = _verified_follow_up_receipt(tool_result.output)
                if receipt is not None:
                    follow_up_brief_fields = _follow_up_brief_fields_from_tool_args(tool_args)
                    verified_follow_up_receipts.append(receipt)
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
    assistant_content = _apply_output_guardrails(
        profile=profile,
        content=assistant_content,
        tool_was_used=tool_was_used,
        verified_action_receipts=verified_action_receipts,
        verified_follow_up_receipts=verified_follow_up_receipts,
        follow_up_brief_fields=follow_up_brief_fields,
    )
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
        model=completion_model,
        latency_ms=latency_ms,
        finish_reason=finish_reason,
        cost_usd=cost_usd,
    )

    result_metadata: dict[str, Any] = {}
    if verified_action_receipts:
        card = verified_action_receipts[-1].get("slack_card")
        if isinstance(card, dict):
            result_metadata["atlas_slack_decision_card"] = card

    return SessionResult(
        messages=result_messages,
        steps=steps_taken,
        finish_reason=finish_reason,
        cost_usd=cost_usd,
        session_id=session_id,
        metadata=result_metadata,
    )


def _extract_tool_call(content: str) -> dict[str, Any] | None:
    """Parse the narrow PF Runtime JSON tool-call envelope."""
    text = content.strip()
    json_start = text.find("{")
    if json_start < 0:
        return None
    text = text[json_start:]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        try:
            payload, _ = json.JSONDecoder().raw_decode(text)
        except json.JSONDecodeError:
            return None
    call = payload.get("tool_call") if isinstance(payload, dict) else None
    if call is None and isinstance(payload, dict):
        call = payload
    if not isinstance(call, dict):
        return None
    name = call.get("name")
    arguments = call.get("arguments")
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return None
    return {"name": name, "arguments": arguments}


def _atlas_model_route_metadata(model: str, content: str) -> dict[str, Any]:
    degraded = "[DEGRADED_MODEL_ROUTE" in content
    if degraded:
        status = "degraded"
    elif model.startswith("anthropic:"):
        status = "premium"
    else:
        status = "smoke"
    return {
        "model_route": model,
        "model_route_status": status,
        "model_route_degraded": degraded,
    }


async def _safe_dispatch(
    dispatcher: ToolDispatcher,
    name: str,
    args: dict[str, Any],
    context: ToolContext,
) -> ToolResult:
    try:
        return await asyncio.wait_for(dispatcher.dispatch(name, args, context), timeout=60)
    except Exception as exc:
        return ToolResult(ok=False, output=None, error=f"{exc.__class__.__name__}: {exc}")


def _degraded_source_packet(source_tool: str, error: str | None) -> dict[str, Any]:
    return {
        "packet_type": "atlas.source_packet.degraded",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "tool": source_tool,
        "source_mode": "degraded",
        "authority": "read_only",
        "sources": [
            {
                "name": source_tool,
                "freshness": "unavailable",
                "confidence": "low",
                "missing": [error or "tool_failed"],
            }
        ],
        "missing_signals": [error or "tool_failed"],
    }


def _model_error_message(profile: Profile, model: str, exc: Exception) -> str:
    detail = f"{exc.__class__.__name__}: {exc}"
    if profile.slug == "atlas-ceo":
        return (
            "Atlas runtime could not complete the model call, so this answer is "
            "degraded and cannot pass a hiring or promotion gate. No action was "
            f"recorded or executed. Model route: {model}. Error: {detail}"
        )
    return (
        "The runtime could not complete the model call. No action was recorded "
        f"or executed. Model route: {model}. Error: {detail}"
    )


_ATLAS_CAPABILITY_TERMS: dict[str, tuple[str, ...]] = {
    "weekly_ceo_brief": (
        "ceo brief",
        "weekly brief",
        "source-grounded",
        "this week",
    ),
    "decision_memo": (
        "decision memo",
        "one-way",
        "two-way",
        "choose between",
        "should atlas",
    ),
    "source_packet_triage": (
        "fleet snapshot",
        "fleet.snapshot",
        "source packet",
        "verified signal",
    ),
    "business_scorecard_brief": (
        "business scorecard",
        "pipeline",
        "proposal",
        "project pulse",
        "current constraint",
    ),
    "action_proposal": (
        "proposal row",
        "propose action",
        "approval proposal",
        "atlas.decision_proposal",
    ),
    "decision_follow_up": (
        "approved decision",
        "follow-up brief",
        "follow up brief",
        "follow-up queued",
        "atlas.follow_up.queued",
        "approval follow-up",
    ),
}


def _atlas_capability_for(profile: Profile, inbound_text: str) -> str | None:
    if profile.slug != "atlas-ceo":
        return None
    lowered = inbound_text.lower()
    if "do not call tools" in lowered or "no-source" in lowered:
        return None
    priority = (
        "action_proposal",
        "decision_follow_up",
        "weekly_ceo_brief",
        "decision_memo",
        "business_scorecard_brief",
        "source_packet_triage",
    )
    for capability in priority:
        terms = _ATLAS_CAPABILITY_TERMS[capability]
        if any(term in lowered for term in terms):
            return capability
    return None


def _source_tool_for_capability(
    capability: str | None,
    tool_names: list[str],
) -> str | None:
    if capability is None:
        return None
    if capability == "business_scorecard_brief" and "business.scorecard.snapshot" in tool_names:
        return "business.scorecard.snapshot"
    if capability in {
        "weekly_ceo_brief",
        "decision_memo",
        "source_packet_triage",
        "action_proposal",
        "decision_follow_up",
    } and "fleet.snapshot" in tool_names:
        return "fleet.snapshot"
    return None


def _atlas_action_proposal_instruction(
    capability: str | None,
    tool_names: list[str],
) -> str:
    if capability != "action_proposal" or "atlas.propose_action" not in tool_names:
        return ""
    return (
        "The user asked to create an approval proposal. If the source packet is "
        "usable, call `atlas.propose_action` before giving the final answer. "
        "Inspect `decision_feedback_recent` before proposing: do not repeat a "
        "recently rejected pattern unless you name what changed, and if "
        "feedback is sparse say so rather than pretending to have learned. "
        "Use the dashboard contract fields: title, summary, recommendation, "
        "decision_kind, priority, horizon, risk_level, reversibility, upside, "
        "downside, next_action, confidence, source_packet_ref or evidence, and "
        "short safe evidence links only. If the tool returns `verified: true` "
        "with an action_id and event_id, say the proposal was recorded and cite "
        "both IDs. If the tool fails or no verified receipt is returned, say only "
        "that the recommendation was drafted, not recorded."
    )


def _atlas_follow_up_instruction(
    capability: str | None,
    tool_names: list[str],
) -> str:
    if capability != "decision_follow_up" or "atlas.record_follow_up" not in tool_names:
        return ""
    return (
        "The user or Slack approval flow asked for an approved-decision "
        "follow-up. Use `follow_up_queue.pending` from the source packet. If "
        "`follow_up_queue.ready_recent` already contains the same "
        "source_action_id, do not create a duplicate. Otherwise call "
        "`atlas.record_follow_up` before the final answer. The final answer "
        "must use exactly these five labels: Approved decision, Next action "
        "for Alex, What Atlas is watching, What not to do, Review timing. "
        "Never claim execution, dispatch, external send, task creation, spend, "
        "deployment, or file/profile changes."
    )


def _atlas_brief_structure_instruction(capability: str | None) -> str:
    if capability not in {
        "weekly_ceo_brief",
        "business_scorecard_brief",
        "source_packet_triage",
        "decision_memo",
    }:
        return ""
    return (
        "For this Atlas source-grounded response, use these exact labels when "
        "applicable: Current constraint, Diagnosis, Top 1-3 priorities, What to "
        "stop doing or Non-priority, Decision Alex must make, Risk Atlas is "
        "watching, Source signal or assumption, Confidence. Never list more "
        "than three priorities. If the packet is stale, missing, or "
        "contradictory, say that directly."
    )


def _needs_atlas_proposal_tool_retry(
    capability: str | None,
    tool_names: list[str],
    proposal_tool_attempted: bool,
    verified_action_receipts: list[dict[str, Any]],
) -> bool:
    return (
        capability == "action_proposal"
        and "atlas.propose_action" in tool_names
        and not proposal_tool_attempted
        and not verified_action_receipts
    )


def _needs_atlas_follow_up_tool_retry(
    capability: str | None,
    tool_names: list[str],
    follow_up_tool_attempted: bool,
    verified_follow_up_receipts: list[dict[str, Any]],
) -> bool:
    return (
        capability == "decision_follow_up"
        and "atlas.record_follow_up" in tool_names
        and not follow_up_tool_attempted
        and not verified_follow_up_receipts
    )


def _select_completion_model(profile: Profile, inbound_text: str) -> str:
    if profile.slug != "atlas-ceo":
        return profile.model
    routing = _profile_model_routing(profile.env_path.parent / "config.yaml")
    lowered = inbound_text.lower()
    if any(term in lowered for term in ("high-stakes", "strategy review")):
        return routing.get("high_stakes_strategy_review", profile.model)
    if _atlas_capability_for(profile, inbound_text) is not None or any(
        term in lowered for term in ("brief", "priority", "priorities")
    ):
        return routing.get("source_grounded_brief", profile.model)
    return profile.model


def _profile_model_routing(config_path: Path) -> dict[str, str]:
    try:
        text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}

    routing: dict[str, str] = {}
    in_model = False
    in_routing = False
    routing_indent = 0
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        stripped = raw.strip()
        indent = len(raw) - len(raw.lstrip(" "))
        if indent == 0:
            in_model = stripped == "model:"
            in_routing = False
            continue
        if in_model and stripped == "routing:":
            in_routing = True
            routing_indent = indent
            continue
        if in_routing:
            if indent <= routing_indent:
                in_routing = False
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                routing[key.strip()] = value.strip().strip('"').strip("'")
    return routing


_ATLAS_METRIC_CLAIM = re.compile(
    r"(\$[\d,.]+|\b\d+(?:\.\d+)?\s?(?:%|percent)\b|\b(?:arr|mrr|revenue|runway|"
    r"burn|churn|cac|ltv|pipeline|conversion|margin|profit)\b)",
    re.IGNORECASE,
)
_ATLAS_ACTION_CLAIM = re.compile(
    r"\b(?:i|atlas)\s+(?:already\s+|have\s+|has\s+)?(?:sent|posted|emailed|"
    r"messaged|published|dispatched|spent|deployed|changed|updated|launched)\b",
    re.IGNORECASE,
)
_ATLAS_PROPOSAL_RECORDED_CLAIM = re.compile(
    r"(\b(?:i|atlas)\s+(?:already\s+|have\s+|has\s+)?"
    r"(?:created|recorded|filed|queued|submitted|opened)\b.{0,80}"
    r"\b(?:proposal|decision|action|row)\b|"
    r"\brecorded\s+(?:pfos\s+)?(?:proposal|decision proposal|action row)\b|"
    r"\b(?:proposal|decision proposal|action row)\b.{0,80}"
    r"\b(?:created|recorded|filed|queued|submitted|opened)\b)",
    re.IGNORECASE | re.DOTALL,
)
_ATLAS_FOLLOW_UP_RECORDED_CLAIM = re.compile(
    r"(\b(?:i|atlas)\s+(?:already\s+|have\s+|has\s+)?"
    r"(?:created|recorded|filed|queued|submitted|opened)\b.{0,80}"
    r"\b(?:follow-up|follow up|followup)\b|"
    r"\brecorded\s+(?:pfos\s+)?(?:follow-up|follow up|followup)\b|"
    r"\b(?:follow-up|follow up|followup)\b.{0,80}"
    r"\b(?:created|recorded|filed|queued|submitted|opened)\b)",
    re.IGNORECASE | re.DOTALL,
)
_ATLAS_ROLE_COLLAPSE = re.compile(
    r"\b(?:jarvis|pm|project manager|sales closer|coder|dispatcher|dispatch agents|"
    r"manage my daily life|client-facing)\b",
    re.IGNORECASE,
)


def _apply_output_guardrails(
    *,
    profile: Profile,
    content: str,
    tool_was_used: bool,
    verified_action_receipts: list[dict[str, Any]] | None = None,
    verified_follow_up_receipts: list[dict[str, Any]] | None = None,
    follow_up_brief_fields: dict[str, str] | None = None,
) -> str:
    """Apply Atlas read-and-recommend guardrails to final text.

    Atlas can inspect approved sources and recommend. It cannot invent metrics
    without a source packet or claim external action from this runtime path.
    """
    if profile.slug != "atlas-ceo":
        return content

    if _atlas_accepted_role_collapse(content):
        return (
            "I need to keep Atlas narrow: CEO operating advisor for Alex, not "
            "Jarvis, PM, coder, sales closer, dispatcher, or client-facing "
            "operator. I can brief the verified business signals, recommend "
            "priorities, and draft approval-needed proposals."
        )

    if _ATLAS_ACTION_CLAIM.search(content):
        return (
            "I cannot claim I sent, posted, approved, changed, or dispatched "
            "anything from this phase. I can inspect approved read-only sources, "
            "draft recommendations, and tell Alex what decision needs approval."
        )

    if _ATLAS_PROPOSAL_RECORDED_CLAIM.search(content) and not verified_action_receipts:
        return (
            "I drafted the recommendation, but I do not have a verified PFOS "
            "proposal receipt for this session. I cannot claim the proposal was "
            "recorded until `atlas.propose_action` returns a verified action_id "
            "and event_id."
        )

    if (
        _ATLAS_FOLLOW_UP_RECORDED_CLAIM.search(content)
        and not verified_follow_up_receipts
    ):
        return (
            "I drafted the follow-up brief, but I do not have a verified PFOS "
            "follow-up event receipt for this session. I cannot claim the "
            "follow-up was recorded until `atlas.record_follow_up` returns a "
            "verified event_id."
        )

    if verified_follow_up_receipts:
        content = _ensure_follow_up_final_answer_fields(
            content,
            receipt=verified_follow_up_receipts[-1],
            fields=follow_up_brief_fields,
        )

    if not tool_was_used and _ATLAS_METRIC_CLAIM.search(content):
        return (
            "I do not have a verified fleet source packet for that claim yet. "
            "Current constraint: insufficient verified signal. I can give a "
            "hypothesis, but a CEO brief needs `fleet.snapshot` or another "
            "approved source before naming metrics, risks, priorities, or trends."
        )

    return content


def _ensure_follow_up_final_answer_fields(
    content: str,
    *,
    receipt: dict[str, Any],
    fields: dict[str, str] | None,
) -> str:
    required_labels = (
        "Approved decision:",
        "Next action for Alex:",
        "What Atlas is watching:",
        "What not to do:",
        "Review timing:",
    )
    if all(label in content for label in required_labels):
        return content
    if not fields:
        return content

    event_id = str(receipt.get("event_id") or "").strip()
    return (
        f"Approved decision: {fields['approved_decision']}\n"
        f"Next action for Alex: {fields['next_action']}\n"
        f"What Atlas is watching: {fields['watch_item']}\n"
        f"What not to do: {fields['non_action']}\n"
        f"Review timing: {fields['review_timing']}\n\n"
        f"Follow-up recorded in PFOS as `{event_id}`. No execution, dispatch, "
        "external send, task creation, spend, deployment, or file/profile "
        "changes occurred."
    )


def _follow_up_brief_fields_from_tool_args(args: dict[str, Any]) -> dict[str, str]:
    return {
        "approved_decision": _safe_text_value(args.get("approved_decision_title")),
        "next_action": _safe_text_value(args.get("next_action")),
        "watch_item": _safe_text_value(args.get("watch_item")),
        "non_action": _safe_text_value(args.get("non_action")),
        "review_timing": _safe_text_value(args.get("review_timing")),
    }


def _safe_text_value(value: Any) -> str:
    text = str(value or "").splitlines()
    joined = " ".join(part.strip() for part in text if part.strip()).strip()
    return joined or "Not specified."


def _verified_action_receipt(output: Any) -> dict[str, Any] | None:
    if not isinstance(output, dict):
        return None
    if (
        output.get("verified") is True
        and isinstance(output.get("action_id"), str)
        and output.get("action_id")
        and isinstance(output.get("event_id"), str)
        and output.get("event_id")
        and output.get("status") == "proposed_only"
        and output.get("executed") is False
    ):
        return dict(output)
    return None


def _verified_follow_up_receipt(output: Any) -> dict[str, Any] | None:
    if not isinstance(output, dict):
        return None
    if (
        output.get("verified") is True
        and isinstance(output.get("event_id"), str)
        and output.get("event_id")
        and output.get("status") == "completed"
        and output.get("executed") is False
    ):
        return dict(output)
    return None


def _atlas_accepted_role_collapse(content: str) -> bool:
    if not _ATLAS_ROLE_COLLAPSE.search(content):
        return False
    return not re.search(
        r"\b(cannot|can't|never|not|narrow|boundary|advisor|refuse)\b",
        content,
        re.IGNORECASE,
    )
