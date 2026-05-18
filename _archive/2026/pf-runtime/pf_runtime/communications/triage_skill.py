"""Communications triage skill (Slice 3 + Slice 4b run-bracket events).

Top-level entry: :func:`triage_all_accounts` walks every account in an
:class:`AccountRegistry` that has credentials, fetches new messages from the
matching provider client, classifies each batch via a :class:`ModelAdapter`,
and proposes actions through :class:`CreateProposalTool` for high-confidence
hits in the proposable bucket set.

Single-message-budget contract:
- One classifier batch per ``batch_size`` messages (no per-message LLM calls).
- Each proposal is a single tool call; the tool persists locally and emits an
  ``ARTIFACT_CREATED`` PFOS event chained under the run id.
- ``triage_all_accounts`` brackets the run with two ``STATE_CHANGED`` PFOS
  events (``pf_runtime_triage_start`` / ``pf_runtime_triage_end``); per-account
  failures emit one ``ERROR`` event each. Emission is fire-and-forget (no-op
  when PFOS env vars are unset).

V1 is read+propose only — this module never mutates a mailbox or calendar; it
only writes proposals through :class:`CreateProposalTool`.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pf_runtime.communications.account_registry import (
    AccountRegistry,
    RegistryEntry,
    RegistryValidationError,
    ScopeViolationError,
)
from pf_runtime.communications.clients import CredentialExpiredError
from pf_runtime.communications.clients.gmail import GmailClient
from pf_runtime.communications.clients.graph import GraphClient
from pf_runtime.communications.clients.imap_hostgator import ImapHostgatorClient
from pf_runtime.communications.providers import (
    normalize_gmail_message,
    normalize_graph_message,
    normalize_imap_message,
)
from pf_runtime.communications.schema import (
    ActionType,
    NormalizedMessage,
    Provider,
    TriageBucket,
)
from pf_runtime.communications.sync_state_store import SyncStateStore
from pf_runtime.communications.tools import (
    AGENT_SLUG,
    SKILL_SLUG,
    CreateProposalTool,
)
from pf_runtime.runtime.pfos_emit import emit_agent_event
from pf_runtime.runtime.tool_dispatch import ToolContext

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Classification:
    """One classifier verdict for a single message.

    ``confidence`` is categorical only — ``"high"`` / ``"medium"`` / ``"low"``.
    Numeric confidences are rejected at parse time.
    """

    bucket: TriageBucket
    confidence: str
    rationale: str


@dataclass(frozen=True)
class AccountTriageResult:
    """Per-account summary of one triage run."""

    account_id: str
    provider: Provider
    fetched: int
    classified: int
    proposed: int
    error: str | None = None


@dataclass(frozen=True)
class TriageRunResult:
    """Aggregate result of a single :func:`triage_all_accounts` run."""

    run_id: str
    started_at: datetime
    finished_at: datetime
    accounts: tuple[AccountTriageResult, ...] = field(default_factory=tuple)

    @property
    def proposals_created(self) -> int:
        return sum(a.proposed for a in self.accounts)

    @property
    def errors(self) -> int:
        return sum(1 for a in self.accounts if a.error is not None)


class ClassifierError(RuntimeError):
    """Classifier output failed JSON / shape / enum validation."""


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------


# Buckets that produce a proposable action. Digest-only buckets
# (NEEDS_ALEX_TODAY / WAITING / FYI) are intentionally excluded so they reach
# Alex via the daily digest only, never the proposal queue.
_PROPOSABLE_BUCKETS: frozenset[TriageBucket] = frozenset(
    {
        TriageBucket.NEEDS_REPLY,
        TriageBucket.SCHEDULE,
        TriageBucket.PROMOTION,
        TriageBucket.NOISE,
        TriageBucket.RELEASE_UPDATE,
    }
)

# Default action proposed for each proposable bucket. The proposal stays in the
# queue for Alex to approve before any provider mutation runs.
_BUCKET_TO_DEFAULT_ACTION: dict[TriageBucket, ActionType] = {
    TriageBucket.NEEDS_REPLY: ActionType.REPLY_DRAFT,
    TriageBucket.SCHEDULE: ActionType.CALENDAR_HOLD,
    TriageBucket.PROMOTION: ActionType.UNSUBSCRIBE_DRAFT,
    TriageBucket.NOISE: ActionType.ARCHIVE,
    TriageBucket.RELEASE_UPDATE: ActionType.LABEL,
}

_VALID_CONFIDENCES: frozenset[str] = frozenset({"high", "medium", "low"})

_SYSTEM_PROMPT = (
    "You are an inbox triage classifier. For each email, return:\n"
    "- bucket: one of needs_alex_today | needs_reply | schedule | waiting | "
    "fyi | promotion | release_update | noise\n"
    "- confidence: high | medium | low\n"
    "- rationale: ≤12 words\n"
    "\n"
    "Output strict JSON: {\"results\": [{\"bucket\": ..., \"confidence\": ..., "
    "\"rationale\": ...}, ...]}.\n"
    "The results array length MUST match the input email count, in the same order.\n"
    "NEVER use numeric confidence — use the categorical strings only."
)

_FENCE_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


# ---------------------------------------------------------------------------
# Client factory contract
# ---------------------------------------------------------------------------


# A client_factory takes a RegistryEntry + SyncStateStore and returns an object
# with a ``.fetch_new()`` method. The default factory reads credentials from
# the process env and instantiates the matching provider client. Tests inject
# a fake factory to avoid network and env coupling.
ClientFactory = Callable[[RegistryEntry, SyncStateStore], Any]


def _credential_env_name(provider: Provider, account_id: str) -> str:
    """Mirror :func:`account_registry._credential_env_name` exactly."""
    prefix_map: dict[Provider, str] = {
        Provider.GOOGLE_MAIL: "PF_GMAIL_TOKEN_",
        Provider.GOOGLE_CALENDAR: "PF_GMAIL_TOKEN_",
        Provider.MICROSOFT_GRAPH: "PF_GRAPH_TOKEN_",
        Provider.IMAP_HOSTGATOR: "PF_IMAP_PASSWORD_",
    }
    safe = account_id.upper().replace("-", "_")
    return f"{prefix_map[provider]}{safe}"


def _default_client_factory(entry: RegistryEntry, sync_store: SyncStateStore) -> Any:
    """Build a provider client from process-env credentials.

    Raises :class:`CredentialExpiredError` when the matching credential env var
    is missing — caller treats this exactly like an expired credential at fetch
    time so Alex sees a single recoverable error path.
    """
    provider = entry.account.provider
    env_name = _credential_env_name(provider, entry.account.account_id)
    secret = os.environ.get(env_name, "").strip()
    if not secret:
        raise CredentialExpiredError(
            f"missing credential env var {env_name} for account "
            f"{entry.account.account_id}"
        )

    if provider is Provider.GOOGLE_MAIL:
        return GmailClient(entry, sync_store, access_token=secret)
    if provider is Provider.MICROSOFT_GRAPH:
        return GraphClient(entry, sync_store, access_token=secret)
    if provider is Provider.IMAP_HOSTGATOR:
        return ImapHostgatorClient(entry, sync_store, password=secret)
    raise RegistryValidationError(
        f"account {entry.account.account_id}: provider {provider.value} has no "
        "default client factory"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def triage_all_accounts(
    registry: AccountRegistry,
    *,
    adapter: Any,
    proposal_tool: CreateProposalTool,
    sync_store: SyncStateStore,
    classifier_model: str,
    profile_slug: str = "personal",
    client_factory: ClientFactory | None = None,
    batch_size: int = 10,
) -> TriageRunResult:
    """Run one triage pass across every credentialled account in ``registry``.

    Emits PFOS run-bracket events (``pf_runtime_triage_start`` /
    ``pf_runtime_triage_end``) plus per-account ``ERROR`` events on failure.
    Each per-account failure is captured into the returned
    :class:`AccountTriageResult` so one bad account never aborts the run.
    """
    started_at = datetime.now(UTC)
    started_perf = time.perf_counter()
    run_id = str(uuid.uuid4())
    factory = client_factory if client_factory is not None else _default_client_factory

    accounts_total = len(registry.entries)
    creds_entries = list(registry.with_credentials())
    accounts_with_creds = len(creds_entries)

    log.info(
        "PFRT_TRIAGE_START run_id=%s accounts_total=%s accounts_with_creds=%s",
        run_id,
        accounts_total,
        accounts_with_creds,
    )

    await emit_agent_event(
        _triage_start_payload(
            run_id=run_id,
            profile_slug=profile_slug,
            accounts_with_credentials=accounts_with_creds,
        )
    )

    results: list[AccountTriageResult] = []
    for entry in creds_entries:
        result = await _triage_account(
            entry=entry,
            adapter=adapter,
            proposal_tool=proposal_tool,
            sync_store=sync_store,
            classifier_model=classifier_model,
            profile_slug=profile_slug,
            run_id=run_id,
            client_factory=factory,
            batch_size=batch_size,
        )
        results.append(result)
        if result.error is not None:
            await emit_agent_event(
                _triage_error_payload(
                    run_id=run_id,
                    profile_slug=profile_slug,
                    account_id=result.account_id,
                    provider=result.provider,
                    error=result.error,
                )
            )

    finished_at = datetime.now(UTC)
    duration_ms = int((time.perf_counter() - started_perf) * 1000)
    proposals = sum(r.proposed for r in results)
    errors = sum(1 for r in results if r.error is not None)

    log.info(
        "PFRT_TRIAGE_END run_id=%s proposals=%s errors=%s duration_ms=%s",
        run_id,
        proposals,
        errors,
        duration_ms,
    )

    await emit_agent_event(
        _triage_end_payload(
            run_id=run_id,
            profile_slug=profile_slug,
            proposals_created=proposals,
            errors=errors,
            duration_ms=duration_ms,
            accounts_scanned=len(results),
        )
    )

    return TriageRunResult(
        run_id=run_id,
        started_at=started_at,
        finished_at=finished_at,
        accounts=tuple(results),
    )


# ---------------------------------------------------------------------------
# Per-account triage
# ---------------------------------------------------------------------------


async def _triage_account(
    *,
    entry: RegistryEntry,
    adapter: Any,
    proposal_tool: CreateProposalTool,
    sync_store: SyncStateStore,
    classifier_model: str,
    profile_slug: str,
    run_id: str,
    client_factory: ClientFactory,
    batch_size: int,
) -> AccountTriageResult:
    """Triage one account end-to-end. Failures are captured, never raised."""
    account_id = entry.account.account_id
    provider = entry.account.provider
    log.info(
        "PFRT_ACCOUNT_FETCH_START account=%s provider=%s",
        account_id,
        provider.value,
    )

    # 1. Build a client. Construction failures (scope / credential / registry
    # validation) are expected error categories — capture them so the run
    # continues for the next account.
    try:
        client = client_factory(entry, sync_store)
    except (
        ScopeViolationError,
        RegistryValidationError,
        CredentialExpiredError,
        ValueError,
    ) as exc:
        err = f"{type(exc).__name__}: {exc}"
        log.error("PFRT_ACCOUNT_FETCH_ERROR account=%s class=%s", account_id, type(exc).__name__)
        return AccountTriageResult(
            account_id=account_id,
            provider=provider,
            fetched=0,
            classified=0,
            proposed=0,
            error=err,
        )

    # 2. Fetch new messages. Provider clients run synchronously and may raise
    # CredentialExpiredError or any other Exception; both go in the error slot.
    try:
        raw = client.fetch_new()
    except CredentialExpiredError as exc:
        err = f"CredentialExpiredError: {exc}"
        log.error(
            "PFRT_ACCOUNT_FETCH_ERROR account=%s class=CredentialExpiredError", account_id
        )
        return AccountTriageResult(
            account_id=account_id,
            provider=provider,
            fetched=0,
            classified=0,
            proposed=0,
            error=err,
        )
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        log.error("PFRT_ACCOUNT_FETCH_ERROR account=%s class=%s", account_id, type(exc).__name__)
        return AccountTriageResult(
            account_id=account_id,
            provider=provider,
            fetched=0,
            classified=0,
            proposed=0,
            error=err,
        )

    fetched_count = len(raw)
    if fetched_count == 0:
        log.info(
            "PFRT_ACCOUNT_FETCH_END account=%s fetched=0 classified=0 proposed=0",
            account_id,
        )
        return AccountTriageResult(
            account_id=account_id,
            provider=provider,
            fetched=0,
            classified=0,
            proposed=0,
        )

    # 3. Normalize to NormalizedMessage. Per-message normalization failures are
    # logged but never abort the account; the batch shrinks accordingly.
    messages: list[NormalizedMessage] = []
    for raw_item in raw:
        try:
            msg = _normalize(entry, raw_item)
        except Exception as exc:
            log.warning(
                "PFRT_NORMALIZE_FAIL account=%s err=%s", account_id, exc
            )
            continue
        messages.append(msg)

    # 4. Classify in batches and propose for high-confidence proposable hits.
    classified_count = 0
    proposed_count = 0
    tool_context = ToolContext(profile_slug=profile_slug, session_id=run_id)

    for batch in _chunk(messages, batch_size):
        try:
            classifications = await _classify_batch(
                adapter=adapter,
                model=classifier_model,
                messages=batch,
            )
        except ClassifierError as exc:
            err = f"ClassifierError: {exc}"
            log.error("PFRT_CLASSIFY_FAIL account=%s err=%s", account_id, exc)
            return AccountTriageResult(
                account_id=account_id,
                provider=provider,
                fetched=fetched_count,
                classified=classified_count,
                proposed=proposed_count,
                error=err,
            )

        classified_count += len(classifications)

        for msg, classification in zip(batch, classifications, strict=True):
            if classification.confidence != "high":
                continue
            if classification.bucket not in _PROPOSABLE_BUCKETS:
                continue
            action_type = _BUCKET_TO_DEFAULT_ACTION[classification.bucket]
            action_id = f"{account_id}-{msg.message_id}-{action_type.value}"
            await proposal_tool.invoke(
                {
                    "action_id": action_id,
                    "action_type": action_type.value,
                    "account_id": account_id,
                    "target_id": msg.message_id,
                    "rationale": classification.rationale,
                    "confidence_bucket": classification.confidence,
                },
                tool_context,
            )
            proposed_count += 1

    log.info(
        "PFRT_ACCOUNT_FETCH_END account=%s fetched=%s classified=%s proposed=%s",
        account_id,
        fetched_count,
        classified_count,
        proposed_count,
    )
    return AccountTriageResult(
        account_id=account_id,
        provider=provider,
        fetched=fetched_count,
        classified=classified_count,
        proposed=proposed_count,
    )


def _normalize(entry: RegistryEntry, raw: Any) -> NormalizedMessage:
    """Dispatch raw provider payload to the matching normalize_* helper."""
    provider = entry.account.provider
    account = entry.account
    if provider is Provider.GOOGLE_MAIL:
        if not isinstance(raw, dict):
            raise TypeError(
                f"gmail raw payload must be dict, got {type(raw).__name__}"
            )
        return normalize_gmail_message(account, raw)
    if provider is Provider.MICROSOFT_GRAPH:
        if not isinstance(raw, dict):
            raise TypeError(
                f"graph raw payload must be dict, got {type(raw).__name__}"
            )
        return normalize_graph_message(account, raw)
    if provider is Provider.IMAP_HOSTGATOR:
        if not isinstance(raw, dict):
            raise TypeError(
                f"imap raw payload must be dict, got {type(raw).__name__}"
            )
        uid = raw.get("uid")
        message = raw.get("message")
        if uid is None or message is None:
            raise ValueError("imap raw payload missing 'uid' or 'message'")
        return normalize_imap_message(account, message, uid=str(uid))
    raise RegistryValidationError(
        f"no normalizer for provider {provider.value}"
    )


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------


async def _classify_batch(
    *,
    adapter: Any,
    model: str,
    messages: list[NormalizedMessage],
) -> list[Classification]:
    """Send one batch through the classifier and parse the strict-JSON response.

    Raises :class:`ClassifierError` when the model's output is not parseable
    JSON, the ``results`` array length disagrees with ``messages``, a bucket
    or confidence value is invalid, or a numeric confidence sneaks through.
    """
    if not messages:
        return []

    user_prompt = "\n".join(
        f"[{idx}] from={m.sender} subject={m.subject!r}\nsnippet={m.snippet[:240]}"
        for idx, m in enumerate(messages)
    )
    chat: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    raw_text, _cost = await _adapter_complete(adapter, chat, model=model)
    return parse_classifier_response(raw_text, expected_count=len(messages))


async def _adapter_complete(
    adapter: Any,
    messages: list[dict[str, Any]],
    *,
    model: str,
) -> tuple[str, Decimal]:
    """Call the adapter; tolerate adapters that don't return Decimal cost."""
    completion: Awaitable[Any] = adapter.complete(messages, model=model, max_tokens=1024)
    raw = await completion
    if isinstance(raw, tuple) and len(raw) == 2:
        text, cost = raw
        return str(text), cost if isinstance(cost, Decimal) else Decimal("0")
    return str(raw), Decimal("0")


def parse_classifier_response(text: str, *, expected_count: int) -> list[Classification]:
    """Parse the strict-JSON response into :class:`Classification` records.

    Strips a single leading/trailing code fence (`````json ...
    `````) before :mod:`json` parsing — adapters frequently wrap
    JSON output in fences even when asked not to.
    """
    cleaned = _strip_code_fence(text)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ClassifierError(f"classifier output not JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ClassifierError(
            f"classifier output must be JSON object, got {type(parsed).__name__}"
        )
    results = parsed.get("results")
    if not isinstance(results, list):
        raise ClassifierError("classifier output missing 'results' array")
    if len(results) != expected_count:
        raise ClassifierError(
            f"classifier returned {len(results)} results; expected {expected_count}"
        )

    out: list[Classification] = []
    for idx, item in enumerate(results):
        if not isinstance(item, dict):
            raise ClassifierError(f"result[{idx}] must be a JSON object")
        for required in ("bucket", "confidence", "rationale"):
            if required not in item:
                raise ClassifierError(
                    f"result[{idx}] missing required field {required!r}"
                )

        confidence_raw = item["confidence"]
        # Defense-in-depth against numeric confidence — even though the prompt
        # forbids it, models occasionally emit floats. We refuse, never coerce.
        if isinstance(confidence_raw, bool) or not isinstance(confidence_raw, str):
            raise ClassifierError(
                f"result[{idx}] confidence must be a string, got "
                f"{type(confidence_raw).__name__}"
            )
        if confidence_raw not in _VALID_CONFIDENCES:
            raise ClassifierError(
                f"result[{idx}] confidence must be one of "
                f"{sorted(_VALID_CONFIDENCES)}; got {confidence_raw!r}"
            )

        bucket_raw = item["bucket"]
        if not isinstance(bucket_raw, str):
            raise ClassifierError(
                f"result[{idx}] bucket must be a string, got "
                f"{type(bucket_raw).__name__}"
            )
        try:
            bucket = TriageBucket(bucket_raw)
        except ValueError as exc:
            raise ClassifierError(
                f"result[{idx}] bucket {bucket_raw!r} is not a valid TriageBucket"
            ) from exc

        rationale_raw = item["rationale"]
        if not isinstance(rationale_raw, str):
            raise ClassifierError(
                f"result[{idx}] rationale must be a string, got "
                f"{type(rationale_raw).__name__}"
            )

        out.append(
            Classification(
                bucket=bucket,
                confidence=confidence_raw,
                rationale=rationale_raw,
            )
        )
    return out


def _strip_code_fence(text: str) -> str:
    """Remove a single ```...``` wrapper if present."""
    match = _FENCE_RE.match(text)
    if match:
        return match.group(1)
    return text.strip()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _chunk(items: list[NormalizedMessage], size: int) -> Iterable[list[NormalizedMessage]]:
    if size <= 0:
        raise ValueError("batch size must be positive")
    for i in range(0, len(items), size):
        yield items[i : i + size]


# ---------------------------------------------------------------------------
# PFOS payload builders (Slice 4b — local because the shape is triage-specific)
# ---------------------------------------------------------------------------


def _triage_start_payload(
    *,
    run_id: str,
    profile_slug: str,
    accounts_with_credentials: int,
) -> dict[str, Any]:
    return {
        "type": "STATE_CHANGED",
        "data": {
            "kind": "pf_runtime_triage_start",
            "run_id": run_id,
            "accounts_with_credentials": accounts_with_credentials,
        },
        "surface": "pf_runtime",
        "agent_slug": AGENT_SLUG,
        "skill_slug": SKILL_SLUG,
        "cwd_project": profile_slug,
        "trace_id": run_id,
    }


def _triage_end_payload(
    *,
    run_id: str,
    profile_slug: str,
    proposals_created: int,
    errors: int,
    duration_ms: int,
    accounts_scanned: int,
) -> dict[str, Any]:
    return {
        "type": "STATE_CHANGED",
        "data": {
            "kind": "pf_runtime_triage_end",
            "run_id": run_id,
            "proposals_created": proposals_created,
            "errors": errors,
            "duration_ms": duration_ms,
            "accounts_scanned": accounts_scanned,
        },
        "surface": "pf_runtime",
        "agent_slug": AGENT_SLUG,
        "skill_slug": SKILL_SLUG,
        "cwd_project": profile_slug,
        "trace_id": run_id,
    }


def _triage_error_payload(
    *,
    run_id: str,
    profile_slug: str,
    account_id: str,
    provider: Provider,
    error: str,
) -> dict[str, Any]:
    return {
        "type": "ERROR",
        "data": {
            "kind": "pf_runtime_triage_error",
            "run_id": run_id,
            "account_id": account_id,
            "provider": provider.value,
            "error": error[:500],
        },
        "surface": "pf_runtime",
        "agent_slug": AGENT_SLUG,
        "skill_slug": SKILL_SLUG,
        "cwd_project": profile_slug,
        "trace_id": run_id,
        "parent_run_id": run_id,
    }


__all__ = [
    "AccountTriageResult",
    "Classification",
    "ClassifierError",
    "TriageRunResult",
    "parse_classifier_response",
    "triage_all_accounts",
]
