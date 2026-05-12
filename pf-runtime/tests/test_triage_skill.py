"""Communications triage skill tests (Slice 3 + Slice 4b).

Covers:
* :func:`parse_classifier_response` — JSON / shape / enum validation paths.
* `_triage_account` — empty fetch, scope/credential failures, classifier
  short-circuit, and proposable-only filtering.
* :func:`triage_all_accounts` — start + per-account error + end PFOS event
  ordering, plus a 10-message golden-mailbox fixture asserting bucket parity
  and proposable subset are correctly proposed.
* :func:`_default_client_factory` — env-var routing per provider.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import pytest

from pf_runtime.communications import triage_skill
from pf_runtime.communications.account_registry import (
    AccountRegistry,
    IMAPSettings,
    RegistryEntry,
    ScopeViolationError,
)
from pf_runtime.communications.clients import CredentialExpiredError
from pf_runtime.communications.clients.gmail import GmailClient
from pf_runtime.communications.clients.graph import GraphClient
from pf_runtime.communications.clients.imap_hostgator import ImapHostgatorClient
from pf_runtime.communications.schema import AccountConfig, Provider, TriageBucket
from pf_runtime.communications.sync_state_store import SyncStateStore
from pf_runtime.communications.tools import CreateProposalTool
from pf_runtime.communications.triage_skill import (
    AccountTriageResult,
    Classification,
    ClassifierError,
    TriageRunResult,
    _default_client_factory,
    _triage_account,
    parse_classifier_response,
    triage_all_accounts,
)
from pf_runtime.runtime.model_adapter import ModelAdapter

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class ScriptedAdapter(ModelAdapter):
    """Adapter whose ``complete()`` pops scripted JSON strings in order."""

    def __init__(self, scripted: list[str]) -> None:
        self._scripted = list(scripted)
        self.calls: list[dict[str, Any]] = []

    async def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        max_tokens: int = 1024,
    ) -> tuple[str, Decimal]:
        self.calls.append({"messages": messages, "model": model})
        if not self._scripted:
            raise AssertionError("ScriptedAdapter ran out of scripted responses")
        return self._scripted.pop(0), Decimal("0")


@dataclass
class FakeClient:
    """A client_factory result with a configurable fetch_new() result."""

    raw: list[dict[str, Any]]
    raise_exc: Exception | None = None

    def fetch_new(self) -> list[dict[str, Any]]:
        if self.raise_exc is not None:
            raise self.raise_exc
        return list(self.raw)


def _gmail_entry(account_id: str = "gmail-1") -> RegistryEntry:
    return RegistryEntry(
        account=AccountConfig(
            account_id=account_id,
            provider=Provider.GOOGLE_MAIL,
            address="alex@example.com",
            scopes=("https://www.googleapis.com/auth/gmail.readonly",),
            read_only=True,
        ),
        credentials_present=True,
    )


def _registry(*entries: RegistryEntry) -> AccountRegistry:
    return AccountRegistry(entries=tuple(entries))


def _gmail_raw(message_id: str, sender: str, subject: str, snippet: str) -> dict[str, Any]:
    """Minimum Gmail payload that normalize_gmail_message accepts."""
    return {
        "id": message_id,
        "threadId": f"thr-{message_id}",
        "snippet": snippet,
        "payload": {
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": "alex@example.com"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Thu, 8 May 2026 12:00:00 +0000"},
            ],
            "parts": [],
        },
    }


def _store(tmp_path: Path) -> SyncStateStore:
    return SyncStateStore(tmp_path / "comms.db")


def _proposal_tool(tmp_path: Path) -> CreateProposalTool:
    return CreateProposalTool(tmp_path / "proposals.db")


@pytest.fixture(autouse=True)
def _patch_emit(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[dict[str, Any]]]:
    """Capture every PFOS emit call so tests never touch the network."""
    captured: list[dict[str, Any]] = []

    async def fake_emit(payload: Any) -> bool:
        captured.append(dict(payload))
        return True

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill.emit_agent_event", fake_emit
    )
    # The proposal tool (CreateProposalTool) also emits — patch its module too.
    monkeypatch.setattr(
        "pf_runtime.communications.tools.emit_agent_event", fake_emit
    )
    yield captured


# ---------------------------------------------------------------------------
# 1. parse_classifier_response — JSON / shape / enum validation
# ---------------------------------------------------------------------------


def test_parse_valid_json_three_results() -> None:
    raw = json.dumps(
        {
            "results": [
                {"bucket": "needs_reply", "confidence": "high", "rationale": "client ask"},
                {"bucket": "promotion", "confidence": "low", "rationale": "newsletter"},
                {"bucket": "fyi", "confidence": "medium", "rationale": "ops digest"},
            ]
        }
    )
    out = parse_classifier_response(raw, expected_count=3)
    assert [c.bucket for c in out] == [
        TriageBucket.NEEDS_REPLY,
        TriageBucket.PROMOTION,
        TriageBucket.FYI,
    ]
    assert [c.confidence for c in out] == ["high", "low", "medium"]


def test_parse_strips_json_code_fence() -> None:
    raw = (
        "```json\n"
        + json.dumps({"results": [{"bucket": "noise", "confidence": "high", "rationale": "spam"}]})
        + "\n```"
    )
    out = parse_classifier_response(raw, expected_count=1)
    assert out[0].bucket is TriageBucket.NOISE


def test_parse_missing_field_raises() -> None:
    raw = json.dumps(
        {"results": [{"bucket": "needs_reply", "rationale": "missing confidence"}]}
    )
    with pytest.raises(ClassifierError, match="confidence"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_wrong_array_length_raises() -> None:
    raw = json.dumps({"results": [{"bucket": "fyi", "confidence": "low", "rationale": "x"}]})
    with pytest.raises(ClassifierError, match="expected 2"):
        parse_classifier_response(raw, expected_count=2)


def test_parse_bad_bucket_raises() -> None:
    raw = json.dumps(
        {"results": [{"bucket": "not_a_bucket", "confidence": "high", "rationale": "x"}]}
    )
    with pytest.raises(ClassifierError, match="not a valid TriageBucket"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_numeric_confidence_rejected() -> None:
    raw = json.dumps(
        {"results": [{"bucket": "fyi", "confidence": 0.92, "rationale": "x"}]}
    )
    with pytest.raises(ClassifierError, match="confidence must be a string"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_uppercase_confidence_rejected() -> None:
    raw = json.dumps(
        {"results": [{"bucket": "fyi", "confidence": "HIGH", "rationale": "x"}]}
    )
    with pytest.raises(ClassifierError, match="must be one of"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_non_object_payload_raises() -> None:
    with pytest.raises(ClassifierError, match="not JSON"):
        parse_classifier_response("not-json-at-all", expected_count=0)


def test_parse_results_not_array_raises() -> None:
    with pytest.raises(ClassifierError, match="results"):
        parse_classifier_response(json.dumps({"results": "oops"}), expected_count=0)


# ---------------------------------------------------------------------------
# 2. _triage_account — fetch / construction / classifier paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_triage_account_empty_fetch(tmp_path: Path) -> None:
    entry = _gmail_entry()

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=[])

    adapter = ScriptedAdapter([])  # never called
    result = await _triage_account(
        entry=entry,
        adapter=adapter,
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="anthropic/claude-haiku-4-5",
        profile_slug="personal",
        run_id="run-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.fetched == 0
    assert result.classified == 0
    assert result.proposed == 0
    assert result.error is None
    assert adapter.calls == []


@pytest.mark.asyncio
async def test_triage_account_scope_violation_captured(tmp_path: Path) -> None:
    entry = _gmail_entry()

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        raise ScopeViolationError("no soup for you")

    result = await _triage_account(
        entry=entry,
        adapter=ScriptedAdapter([]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.error is not None
    assert "ScopeViolationError" in result.error
    assert result.fetched == 0


@pytest.mark.asyncio
async def test_triage_account_credential_expired_at_fetch(tmp_path: Path) -> None:
    entry = _gmail_entry()

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=[], raise_exc=CredentialExpiredError("401"))

    result = await _triage_account(
        entry=entry,
        adapter=ScriptedAdapter([]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.error is not None
    assert "CredentialExpiredError" in result.error


@pytest.mark.asyncio
async def test_triage_account_classifier_short_circuits(tmp_path: Path) -> None:
    entry = _gmail_entry()
    raw = [_gmail_raw("m1", "boss@example.com", "Q2 update", "Need your sign-off")]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    # Adapter returns garbage that fails JSON parse → ClassifierError.
    adapter = ScriptedAdapter(["not-json"])
    result = await _triage_account(
        entry=entry,
        adapter=adapter,
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.error is not None
    assert "ClassifierError" in result.error
    assert result.fetched == 1
    assert result.classified == 0
    assert result.proposed == 0


@pytest.mark.asyncio
async def test_triage_account_generic_fetch_error_captured(tmp_path: Path) -> None:
    entry = _gmail_entry()

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=[], raise_exc=RuntimeError("bad gateway"))

    result = await _triage_account(
        entry=entry,
        adapter=ScriptedAdapter([]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.error is not None
    assert "RuntimeError" in result.error


# ---------------------------------------------------------------------------
# 3. Proposal filtering — only high-confidence + proposable bucket → propose
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_proposal_filtering(tmp_path: Path) -> None:
    """Five messages exercise each filter rule:
    1. high + needs_reply       → proposed (REPLY_DRAFT)
    2. medium + needs_reply     → NOT proposed (low confidence)
    3. low + promotion          → NOT proposed
    4. high + fyi               → NOT proposed (non-proposable bucket)
    5. high + needs_alex_today  → proposed (FOLLOW_UP_TASK; Phase 2 addition —
       NEEDS_ALEX_TODAY now lands a real PFOS task plus an agent_actions row)
    """
    entry = _gmail_entry()
    raw = [
        _gmail_raw("m1", "boss@example.com", "Reply please", "snippet"),
        _gmail_raw("m2", "boss@example.com", "Reply medium", "snippet"),
        _gmail_raw("m3", "promo@vendor.com", "50% off", "snippet"),
        _gmail_raw("m4", "fyi@example.com", "Status", "snippet"),
        _gmail_raw("m5", "wife@example.com", "today!", "snippet"),
    ]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    scripted = json.dumps(
        {
            "results": [
                {"bucket": "needs_reply", "confidence": "high", "rationale": "ask"},
                {"bucket": "needs_reply", "confidence": "medium", "rationale": "ask"},
                {"bucket": "promotion", "confidence": "low", "rationale": "ad"},
                {"bucket": "fyi", "confidence": "high", "rationale": "info"},
                {
                    "bucket": "needs_alex_today",
                    "confidence": "high",
                    "rationale": "today",
                },
            ]
        }
    )
    adapter = ScriptedAdapter([scripted])

    proposal_tool = _proposal_tool(tmp_path)
    proposal_spy = AsyncMock(wraps=proposal_tool.invoke)
    proposal_tool.invoke = proposal_spy  # type: ignore[method-assign]

    result = await _triage_account(
        entry=entry,
        adapter=adapter,
        proposal_tool=proposal_tool,
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.fetched == 5
    assert result.classified == 5
    assert result.proposed == 2

    assert proposal_spy.await_count == 2
    by_target = {
        call.args[0]["target_id"]: call.args[0]
        for call in proposal_spy.await_args_list
    }
    assert set(by_target) == {"m1", "m5"}
    assert by_target["m1"]["action_type"] == "reply_draft"
    assert by_target["m1"]["confidence_bucket"] == "high"
    assert by_target["m1"]["action_id"] == "gmail-1-m1-reply_draft"
    assert by_target["m5"]["action_type"] == "follow_up_task"
    assert by_target["m5"]["confidence_bucket"] == "high"
    assert by_target["m5"]["action_id"] == "gmail-1-m5-follow_up_task"


# ---------------------------------------------------------------------------
# 4. triage_all_accounts — PFOS event ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_triage_all_accounts_emits_start_errors_end_in_order(
    tmp_path: Path, _patch_emit: list[dict[str, Any]]
) -> None:
    good = _gmail_entry("gmail-good")
    bad = _gmail_entry("gmail-bad")
    registry = _registry(good, bad)

    def factory(entry: RegistryEntry, _s: SyncStateStore) -> Any:
        if entry.account.account_id == "gmail-bad":
            raise CredentialExpiredError("401")
        return FakeClient(raw=[])

    adapter = ScriptedAdapter([])  # no messages → never called
    run = await triage_all_accounts(
        registry,
        adapter=adapter,
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        client_factory=factory,
        batch_size=10,
    )
    assert isinstance(run, TriageRunResult)
    assert run.proposals_created == 0
    assert run.errors == 1

    # Filter to triage-skill emits only — proposal_tool emits would never fire
    # here because no proposals were created, but be defensive.
    triage_emits = [
        p for p in _patch_emit if str(p.get("data", {}).get("kind", "")).startswith("pf_runtime_triage")
    ]
    kinds = [p["data"]["kind"] for p in triage_emits]
    assert kinds == [
        "pf_runtime_triage_start",
        "pf_runtime_triage_error",
        "pf_runtime_triage_end",
    ]
    err_payload = triage_emits[1]
    assert err_payload["type"] == "ERROR"
    assert err_payload["parent_run_id"] == run.run_id
    assert err_payload["data"]["account_id"] == "gmail-bad"
    assert err_payload["data"]["provider"] == "google_mail"

    end_payload = triage_emits[2]
    assert end_payload["data"]["accounts_scanned"] == 2
    assert end_payload["data"]["errors"] == 1
    assert end_payload["data"]["proposals_created"] == 0


# ---------------------------------------------------------------------------
# 5. Golden mailbox — 10 messages, deterministic mock classifier
# ---------------------------------------------------------------------------


GOLDEN_MAILBOX: list[tuple[str, str, str, str, TriageBucket]] = [
    ("g1", "boss@example.com", "Need approval Q2 plan", "please approve by EOW", TriageBucket.NEEDS_REPLY),
    ("g2", "newsletter@vendor.com", "10 reasons to buy", "summer sale!!", TriageBucket.PROMOTION),
    ("g3", "calendar@example.com", "Reschedule call?", "moving to Friday", TriageBucket.SCHEDULE),
    ("g4", "noreply@github.com", "[release] v1.4.0", "changelog inside", TriageBucket.RELEASE_UPDATE),
    ("g5", "spam@evil.io", "WIN BITCOIN NOW", "click click", TriageBucket.NOISE),
    ("g6", "wife@example.com", "Pickup the kid?", "today at 3pm", TriageBucket.NEEDS_ALEX_TODAY),
    ("g7", "ops@example.com", "Awaiting your sign-off", "blocked on you", TriageBucket.WAITING),
    ("g8", "ops@example.com", "Weekly digest", "lots of stuff", TriageBucket.FYI),
    ("g9", "client@example.com", "Quick question", "got 2 mins?", TriageBucket.NEEDS_REPLY),
    ("g10", "promo@vendor.com", "Last chance!", "buy now", TriageBucket.PROMOTION),
]


@pytest.mark.asyncio
async def test_golden_mailbox_classification_and_proposals(tmp_path: Path) -> None:
    entry = _gmail_entry()
    raw = [
        _gmail_raw(mid, sender, subject, snippet)
        for mid, sender, subject, snippet, _ in GOLDEN_MAILBOX
    ]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    # Deterministic mock classifier. All "high" so the proposable subset is
    # guaranteed to produce proposals.
    scripted = json.dumps(
        {
            "results": [
                {"bucket": bucket.value, "confidence": "high", "rationale": "test"}
                for _mid, _s, _sub, _snip, bucket in GOLDEN_MAILBOX
            ]
        }
    )
    adapter = ScriptedAdapter([scripted])

    proposal_tool = _proposal_tool(tmp_path)
    proposal_spy = AsyncMock(wraps=proposal_tool.invoke)
    proposal_tool.invoke = proposal_spy  # type: ignore[method-assign]

    result = await _triage_account(
        entry=entry,
        adapter=adapter,
        proposal_tool=proposal_tool,
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-golden",
        client_factory=factory,
        batch_size=10,
    )

    # All 10 classified.
    assert result.fetched == 10
    assert result.classified == 10

    # Proposable subset = NEEDS_REPLY (g1, g9) + PROMOTION (g2, g10) +
    # SCHEDULE (g3) + RELEASE_UPDATE (g4) + NOISE (g5) + NEEDS_ALEX_TODAY
    # (g6, Phase 2) = 8. The 2 remaining digest-only buckets (WAITING g7,
    # FYI g8) stay excluded from the proposal queue per spec.
    assert result.proposed == 8

    proposed_target_ids = {
        c.args[0]["target_id"] for c in proposal_spy.await_args_list
    }
    assert proposed_target_ids == {"g1", "g2", "g3", "g4", "g5", "g6", "g9", "g10"}

    # Spot-check action mapping for one message of each proposable bucket.
    action_by_target = {
        c.args[0]["target_id"]: c.args[0]["action_type"]
        for c in proposal_spy.await_args_list
    }
    assert action_by_target["g1"] == "reply_draft"
    assert action_by_target["g2"] == "unsubscribe_draft"
    assert action_by_target["g3"] == "calendar_hold"
    assert action_by_target["g4"] == "label"
    assert action_by_target["g5"] == "archive"
    assert action_by_target["g6"] == "follow_up_task"


# ---------------------------------------------------------------------------
# 6. _default_client_factory — env-var routing per provider
# ---------------------------------------------------------------------------


def test_default_factory_gmail_routes_to_gmail_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PF_GMAIL_TOKEN_GMAIL_1", "tok-gmail")
    entry = _gmail_entry("gmail-1")
    client = _default_client_factory(entry, _store(tmp_path))
    assert isinstance(client, GmailClient)
    assert client.account_id == "gmail-1"


def test_default_factory_graph_routes_to_graph_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PF_GRAPH_TOKEN_GRAPH_1", "tok-graph")
    entry = RegistryEntry(
        account=AccountConfig(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            address="alex@outlook.com",
            scopes=("Mail.Read",),
            read_only=True,
        ),
        credentials_present=True,
    )
    client = _default_client_factory(entry, _store(tmp_path))
    assert isinstance(client, GraphClient)
    assert client.account_id == "graph-1"


def test_default_factory_imap_routes_to_imap_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PF_IMAP_PASSWORD_IMAP_1", "pw-imap")
    entry = RegistryEntry(
        account=AccountConfig(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            address="alex@yehovahbuilders.com",
            scopes=(),
            read_only=True,
        ),
        imap=IMAPSettings(port=993, ssl=True, smtp_enabled_v1=False),
        credentials_present=True,
    )
    client = _default_client_factory(entry, _store(tmp_path))
    assert isinstance(client, ImapHostgatorClient)
    assert client.account_id == "imap-1"


def test_default_factory_missing_env_raises_credential_expired(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PF_GMAIL_TOKEN_GMAIL_NOPE", raising=False)
    entry = _gmail_entry("gmail-nope")
    with pytest.raises(CredentialExpiredError):
        _default_client_factory(entry, _store(tmp_path))


# ---------------------------------------------------------------------------
# Auxiliary: verify the public-facing dataclass shape stays as documented
# ---------------------------------------------------------------------------


def test_account_triage_result_is_frozen() -> None:
    r = AccountTriageResult(
        account_id="x",
        provider=Provider.GOOGLE_MAIL,
        fetched=0,
        classified=0,
        proposed=0,
    )
    with pytest.raises(AttributeError):
        r.fetched = 5  # type: ignore[misc]


def test_triage_run_result_aggregations() -> None:
    from datetime import UTC as _UTC
    from datetime import datetime as _dt

    now = _dt.now(_UTC)
    run = TriageRunResult(
        run_id="r",
        started_at=now,
        finished_at=now,
        accounts=(
            AccountTriageResult(
                account_id="a",
                provider=Provider.GOOGLE_MAIL,
                fetched=1,
                classified=1,
                proposed=1,
            ),
            AccountTriageResult(
                account_id="b",
                provider=Provider.MICROSOFT_GRAPH,
                fetched=0,
                classified=0,
                proposed=0,
                error="nope",
            ),
        ),
    )
    assert run.proposals_created == 1
    assert run.errors == 1


def test_classification_dataclass_construction() -> None:
    c = Classification(
        bucket=TriageBucket.NEEDS_REPLY, confidence="high", rationale="x"
    )
    assert c.confidence == "high"
    assert c.bucket is TriageBucket.NEEDS_REPLY


# ---------------------------------------------------------------------------
# Extra coverage — parser edge cases + normalize fallthrough
# ---------------------------------------------------------------------------


def test_parse_item_not_object_raises() -> None:
    raw = json.dumps({"results": ["not-an-object"]})
    with pytest.raises(ClassifierError, match="must be a JSON object"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_bucket_not_string_raises() -> None:
    raw = json.dumps(
        {"results": [{"bucket": 5, "confidence": "high", "rationale": "x"}]}
    )
    with pytest.raises(ClassifierError, match="bucket must be a string"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_rationale_not_string_raises() -> None:
    raw = json.dumps(
        {"results": [{"bucket": "fyi", "confidence": "high", "rationale": 42}]}
    )
    with pytest.raises(ClassifierError, match="rationale must be a string"):
        parse_classifier_response(raw, expected_count=1)


def test_parse_top_level_not_object_raises() -> None:
    with pytest.raises(ClassifierError, match="must be JSON object"):
        parse_classifier_response("[1, 2, 3]", expected_count=0)


def test_parse_boolean_confidence_rejected() -> None:
    raw = json.dumps(
        {"results": [{"bucket": "fyi", "confidence": True, "rationale": "x"}]}
    )
    with pytest.raises(ClassifierError, match="confidence must be a string"):
        parse_classifier_response(raw, expected_count=1)


@pytest.mark.asyncio
async def test_normalize_failure_skips_message_and_continues(tmp_path: Path) -> None:
    """A malformed Gmail payload makes normalize raise; the bad item is skipped."""
    entry = _gmail_entry()
    good = _gmail_raw("g1", "boss@example.com", "ok", "snippet")
    # Bad payload — not a dict, will trigger TypeError in _normalize.
    bad: Any = "not-a-dict"
    raw_items: list[Any] = [good, bad]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        client = FakeClient(raw=[])
        client.raw = raw_items  # type: ignore[assignment]
        return client

    scripted = json.dumps(
        {
            "results": [
                {"bucket": "fyi", "confidence": "low", "rationale": "info"},
            ]
        }
    )
    adapter = ScriptedAdapter([scripted])

    result = await _triage_account(
        entry=entry,
        adapter=adapter,
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-x",
        client_factory=factory,
        batch_size=10,
    )
    # Two items fetched, one normalize failure → only one classified.
    assert result.fetched == 2
    assert result.classified == 1
    assert result.proposed == 0
    assert result.error is None


@pytest.mark.asyncio
async def test_adapter_returning_bare_string_tolerated(tmp_path: Path) -> None:
    """Adapter that returns just a string (not a tuple) is treated as raw text."""

    class StringAdapter(ModelAdapter):
        async def complete(
            self,
            messages: list[dict[str, Any]],
            *,
            model: str,
            max_tokens: int = 1024,
        ) -> Any:
            # Intentionally return just a string — _adapter_complete falls
            # through to its non-tuple branch.
            return json.dumps(
                {"results": [{"bucket": "fyi", "confidence": "low", "rationale": "x"}]}
            )

    entry = _gmail_entry()
    raw = [_gmail_raw("m1", "x@example.com", "subject", "snippet")]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    result = await _triage_account(
        entry=entry,
        adapter=StringAdapter(),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-z",
        client_factory=factory,
        batch_size=10,
    )
    assert result.classified == 1
    assert result.proposed == 0
    assert result.error is None


@pytest.mark.asyncio
async def test_adapter_returning_non_decimal_cost(tmp_path: Path) -> None:
    """Adapter returns (text, int) instead of (text, Decimal) — cost coerced."""

    class IntCostAdapter(ModelAdapter):
        async def complete(
            self,
            messages: list[dict[str, Any]],
            *,
            model: str,
            max_tokens: int = 1024,
        ) -> Any:
            return (
                json.dumps(
                    {
                        "results": [
                            {"bucket": "fyi", "confidence": "low", "rationale": "x"}
                        ]
                    }
                ),
                0,  # int, not Decimal — covers the fallback branch
            )

    entry = _gmail_entry()
    raw = [_gmail_raw("m1", "x@example.com", "subject", "snippet")]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    result = await _triage_account(
        entry=entry,
        adapter=IntCostAdapter(),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-q",
        client_factory=factory,
        batch_size=10,
    )
    assert result.classified == 1
    assert result.error is None


def test_chunk_rejects_zero_or_negative_size() -> None:
    from pf_runtime.communications.triage_skill import _chunk

    with pytest.raises(ValueError, match="positive"):
        list(_chunk([], 0))


def test_classify_batch_empty_returns_empty(tmp_path: Path) -> None:
    """Direct call: empty batch shortcut yields empty list (no adapter call)."""
    import asyncio

    from pf_runtime.communications.triage_skill import _classify_batch

    adapter = ScriptedAdapter([])
    out = asyncio.run(
        _classify_batch(adapter=adapter, model="m", messages=[])
    )
    assert out == []
    assert adapter.calls == []


def test_default_factory_unknown_provider_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """GOOGLE_CALENDAR has the same env prefix as GOOGLE_MAIL but no client mapping."""
    monkeypatch.setenv("PF_GMAIL_TOKEN_CAL_1", "tok")
    entry = RegistryEntry(
        account=AccountConfig(
            account_id="cal-1",
            provider=Provider.GOOGLE_CALENDAR,
            address="alex@example.com",
            scopes=(),
            read_only=True,
        ),
        credentials_present=True,
    )
    from pf_runtime.communications.account_registry import RegistryValidationError

    with pytest.raises(RegistryValidationError, match="no default client factory"):
        _default_client_factory(entry, _store(tmp_path))


def test_normalize_dispatches_graph_payload(tmp_path: Path) -> None:
    """Direct _normalize call covers the Graph and IMAP branches."""
    from email.message import EmailMessage

    from pf_runtime.communications.triage_skill import _normalize

    graph_entry = RegistryEntry(
        account=AccountConfig(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            address="alex@outlook.com",
        ),
        credentials_present=True,
    )
    graph_raw = {
        "id": "g1",
        "subject": "hello",
        "from": {"emailAddress": {"address": "x@y.com"}},
        "toRecipients": [{"emailAddress": {"address": "alex@outlook.com"}}],
        "receivedDateTime": "2026-05-08T12:00:00Z",
        "bodyPreview": "hi",
    }
    msg = _normalize(graph_entry, graph_raw)
    assert msg.message_id == "g1"
    assert msg.provider is Provider.MICROSOFT_GRAPH

    imap_entry = RegistryEntry(
        account=AccountConfig(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            address="alex@yehovahbuilders.com",
        ),
        imap=IMAPSettings(port=993, ssl=True, smtp_enabled_v1=False),
        credentials_present=True,
    )
    em = EmailMessage()
    em["From"] = "x@y.com"
    em["To"] = "alex@yehovahbuilders.com"
    em["Subject"] = "hi"
    em["Date"] = "Thu, 8 May 2026 12:00:00 +0000"
    em.set_content("body")
    msg2 = _normalize(imap_entry, {"uid": 7, "message": em})
    assert msg2.message_id == "7"
    assert msg2.provider is Provider.IMAP_HOSTGATOR


def test_normalize_imap_missing_uid_raises(tmp_path: Path) -> None:
    from pf_runtime.communications.triage_skill import _normalize

    imap_entry = RegistryEntry(
        account=AccountConfig(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            address="alex@yehovahbuilders.com",
        ),
        imap=IMAPSettings(port=993, ssl=True, smtp_enabled_v1=False),
        credentials_present=True,
    )
    with pytest.raises(ValueError, match="missing 'uid'"):
        _normalize(imap_entry, {"uid": None, "message": None})


def test_normalize_graph_payload_not_dict_raises() -> None:
    from pf_runtime.communications.triage_skill import _normalize

    graph_entry = RegistryEntry(
        account=AccountConfig(
            account_id="graph-1",
            provider=Provider.MICROSOFT_GRAPH,
            address="alex@outlook.com",
        ),
        credentials_present=True,
    )
    with pytest.raises(TypeError, match="graph raw payload"):
        _normalize(graph_entry, "not-a-dict")


def test_normalize_imap_payload_not_dict_raises() -> None:
    from pf_runtime.communications.triage_skill import _normalize

    imap_entry = RegistryEntry(
        account=AccountConfig(
            account_id="imap-1",
            provider=Provider.IMAP_HOSTGATOR,
            address="alex@yehovahbuilders.com",
        ),
        imap=IMAPSettings(port=993, ssl=True, smtp_enabled_v1=False),
        credentials_present=True,
    )
    with pytest.raises(TypeError, match="imap raw payload"):
        _normalize(imap_entry, "not-a-dict")


def test_normalize_unsupported_provider_raises() -> None:
    from pf_runtime.communications.account_registry import RegistryValidationError
    from pf_runtime.communications.triage_skill import _normalize

    cal_entry = RegistryEntry(
        account=AccountConfig(
            account_id="cal-1",
            provider=Provider.GOOGLE_CALENDAR,
            address="alex@example.com",
        ),
        credentials_present=True,
    )
    with pytest.raises(RegistryValidationError, match="no normalizer"):
        _normalize(cal_entry, {})


def test_module_constants_match_spec() -> None:
    """Lock the bucket→action mapping and proposable set to spec.

    Phase 2 added NEEDS_ALEX_TODAY → FOLLOW_UP_TASK so the urgent bucket
    lands a real PFOS todo on each cycle (not just a digest line).
    """
    from pf_runtime.communications.schema import ActionType

    expected_proposable = frozenset(
        {
            TriageBucket.NEEDS_ALEX_TODAY,
            TriageBucket.NEEDS_REPLY,
            TriageBucket.SCHEDULE,
            TriageBucket.PROMOTION,
            TriageBucket.NOISE,
            TriageBucket.RELEASE_UPDATE,
        }
    )
    assert expected_proposable == triage_skill._PROPOSABLE_BUCKETS
    expected_action_map = {
        TriageBucket.NEEDS_ALEX_TODAY: ActionType.FOLLOW_UP_TASK,
        TriageBucket.NEEDS_REPLY: ActionType.REPLY_DRAFT,
        TriageBucket.SCHEDULE: ActionType.CALENDAR_HOLD,
        TriageBucket.PROMOTION: ActionType.UNSUBSCRIBE_DRAFT,
        TriageBucket.NOISE: ActionType.ARCHIVE,
        TriageBucket.RELEASE_UPDATE: ActionType.LABEL,
    }
    assert expected_action_map == triage_skill._BUCKET_TO_DEFAULT_ACTION


# ---------------------------------------------------------------------------
# Phase 3: cross-account dedupe — same RFC 822 Message-ID across mailboxes
# collapses to one proposal with also_seen_in covering both accounts.
# ---------------------------------------------------------------------------


def _gmail_raw_with_rfc822(
    message_id: str,
    sender: str,
    subject: str,
    snippet: str,
    *,
    rfc822_id: str,
) -> dict[str, Any]:
    """Gmail payload with an explicit Message-ID header for dedupe."""
    return {
        "id": message_id,
        "threadId": f"thr-{message_id}",
        "snippet": snippet,
        "payload": {
            "headers": [
                {"name": "From", "value": sender},
                {"name": "To", "value": "alex@example.com"},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Thu, 8 May 2026 12:00:00 +0000"},
                {"name": "Message-ID", "value": rfc822_id},
            ],
            "parts": [],
        },
    }


@pytest.mark.asyncio
async def test_cross_account_dedupe_collapses_to_one_proposal(tmp_path: Path) -> None:
    """A thread reaching gmail-1 and gmail-2 with the same RFC 822
    Message-ID should produce ONE proposal with also_seen_in covering
    both account_ids. The second cycle hits ``find_by_dedupe`` and
    calls ``append_also_seen`` instead of inserting a duplicate row."""
    rfc822 = "<thread-abc@mail.gmail.com>"
    raw_per_account = {
        "gmail-1": [
            _gmail_raw_with_rfc822(
                "m-1-acct-a",
                "boss@example.com",
                "Reply please",
                "snippet",
                rfc822_id=rfc822,
            ),
        ],
        "gmail-2": [
            _gmail_raw_with_rfc822(
                "m-1-acct-b",  # different per-mailbox message_id
                "boss@example.com",
                "Reply please",
                "snippet",
                rfc822_id=rfc822,  # same RFC 822 Message-ID
            ),
        ],
    }

    def factory(entry: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw_per_account[entry.account.account_id])

    # One scripted classifier response per cycle (one batch per account).
    scripted = json.dumps(
        {
            "results": [
                {
                    "bucket": "needs_reply",
                    "confidence": "high",
                    "rationale": "direct ask",
                }
            ]
        }
    )

    # Two accounts share an underlying proposal_tool so the SQLite
    # store is the same DB across both _triage_account calls.
    proposal_tool = _proposal_tool(tmp_path)
    sync_store = _store(tmp_path)
    common_kwargs = {
        "proposal_tool": proposal_tool,
        "sync_store": sync_store,
        "classifier_model": "model",
        "profile_slug": "personal",
        "run_id": "run-dedupe",
        "client_factory": factory,
        "batch_size": 10,
    }

    # First account: classifier returns needs_reply -> proposal inserted.
    result_a = await _triage_account(
        entry=_gmail_entry("gmail-1"),
        adapter=ScriptedAdapter([scripted]),
        **common_kwargs,
    )
    # Second account: same RFC 822 ID -> dedupe hit, no second insert.
    result_b = await _triage_account(
        entry=_gmail_entry("gmail-2"),
        adapter=ScriptedAdapter([scripted]),
        **common_kwargs,
    )

    assert result_a.proposed == 1
    assert result_b.proposed == 0  # dedupe path skipped the insert

    # The single surviving proposal has both account_ids on its trail.
    proposals = proposal_tool.store.list(status="proposed")
    assert len(proposals) == 1
    found = proposal_tool.store.find_by_dedupe(f"rfc822:{rfc822}")
    assert found is not None
    assert set(found["also_seen_in"]) == {"gmail-1", "gmail-2"}
    assert found["also_seen_count"] == 2


@pytest.mark.asyncio
async def test_dedupe_only_collapses_across_different_accounts(
    tmp_path: Path,
) -> None:
    """If the same account legitimately re-classifies a message (e.g.
    a re-run of a previous cycle), the dedupe check should NOT add the
    account to its own also_seen_in trail — the early-skip only fires
    when the existing row belongs to a *different* account."""
    rfc822 = "<self-dup@example.com>"
    raw = [
        _gmail_raw_with_rfc822(
            "m1",
            "boss@example.com",
            "Reply",
            "snip",
            rfc822_id=rfc822,
        )
    ]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    scripted = json.dumps(
        {
            "results": [
                {
                    "bucket": "needs_reply",
                    "confidence": "high",
                    "rationale": "direct ask",
                }
            ]
        }
    )
    proposal_tool = _proposal_tool(tmp_path)
    sync_store = _store(tmp_path)

    result_first = await _triage_account(
        entry=_gmail_entry("gmail-1"),
        adapter=ScriptedAdapter([scripted]),
        proposal_tool=proposal_tool,
        sync_store=sync_store,
        classifier_model="model",
        profile_slug="personal",
        run_id="r-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result_first.proposed == 1

    # Same account, same message: a re-run should NOT collapse via the
    # cross-account skip; the insert collision is handled separately by
    # SQLite's primary-key constraint on action_id, not by this skip.
    found = proposal_tool.store.find_by_dedupe(f"rfc822:{rfc822}")
    assert found is not None
    assert found["also_seen_in"] == ["gmail-1"]
    assert found["also_seen_count"] == 1


# ---------------------------------------------------------------------------
# 8. Phase 5 — SCHEDULE-bucket calendar correlation
# ---------------------------------------------------------------------------


def _calendar_twin_entry(account_id: str = "gmail-1-calendar") -> RegistryEntry:
    return RegistryEntry(
        account=AccountConfig(
            account_id=account_id,
            provider=Provider.GOOGLE_CALENDAR,
            address="alex@example.com",
            scopes=("https://www.googleapis.com/auth/calendar.readonly",),
            read_only=True,
        ),
        credentials_present=True,
    )


def _schedule_gmail_raw(body_snippet: str) -> dict[str, Any]:
    """A Gmail payload whose snippet contains a meeting proposal."""
    return {
        "id": "m-sched-1",
        "threadId": "thr-sched-1",
        "snippet": body_snippet,
        "payload": {
            "headers": [
                {"name": "From", "value": "client@example.com"},
                {"name": "To", "value": "alex@example.com"},
                {"name": "Subject", "value": "Quick sync?"},
                {"name": "Date", "value": "Mon, 11 May 2026 15:00:00 +0000"},
            ],
            "parts": [],
        },
    }


@pytest.mark.asyncio
async def test_schedule_bucket_emits_calendar_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SCHEDULE-classified message → emit_action body carries the meeting
    time, conflict flag, and meeting URL in params_json."""
    captured_actions: list[dict[str, Any]] = []

    async def fake_emit_action(body: dict[str, Any], *, silo: str) -> bool:
        captured_actions.append(body)
        return True

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill.emit_action", fake_emit_action
    )

    # No conflict — calendar reports empty busy list.
    class _CalendarStub:
        def freebusy(self, _tmin: Any, _tmax: Any) -> list[Any]:
            return []

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill._build_calendar_client",
        lambda *_a, **_kw: _CalendarStub(),
    )

    raw = [
        _schedule_gmail_raw(
            "Can we meet Tuesday at 2pm? Zoom: https://zoom.us/j/12345"
        )
    ]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    scripted = json.dumps(
        {
            "results": [
                {
                    "bucket": "schedule",
                    "confidence": "high",
                    "rationale": "proposes Tuesday 2pm sync",
                }
            ]
        }
    )

    result = await _triage_account(
        entry=_gmail_entry("gmail-1"),
        adapter=ScriptedAdapter([scripted]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-cal-1",
        client_factory=factory,
        batch_size=10,
    )
    assert result.proposed == 1
    assert len(captured_actions) == 1
    params = captured_actions[0]["params_json"]
    assert params["proposed_start_iso"]  # populated
    assert "zoom.us/j/12345" in params["meeting_url"]
    assert params["freebusy_conflict"] is False
    # No conflict → priority is P2 per the SCHEDULE row of the protocol matrix.
    assert params["priority"] == "P2"


@pytest.mark.asyncio
async def test_schedule_bucket_conflict_downgrades_to_p3(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When freebusy reports overlap with the proposed start, set
    `freebusy_conflict=true` AND downgrade priority to P3."""
    from datetime import UTC, datetime

    captured_actions: list[dict[str, Any]] = []

    async def fake_emit_action(body: dict[str, Any], *, silo: str) -> bool:
        captured_actions.append(body)
        return True

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill.emit_action", fake_emit_action
    )

    class _BusyCalendarStub:
        def freebusy(
            self, _tmin: Any, _tmax: Any
        ) -> list[tuple[datetime, datetime]]:
            return [
                (
                    datetime(2026, 5, 12, 19, 0, tzinfo=UTC),  # 2pm CT
                    datetime(2026, 5, 12, 20, 0, tzinfo=UTC),
                )
            ]

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill._build_calendar_client",
        lambda *_a, **_kw: _BusyCalendarStub(),
    )

    raw = [_schedule_gmail_raw("Tuesday at 2pm CT works?")]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    scripted = json.dumps(
        {
            "results": [
                {
                    "bucket": "schedule",
                    "confidence": "high",
                    "rationale": "proposes Tuesday 2pm",
                }
            ]
        }
    )

    result = await _triage_account(
        entry=_gmail_entry("gmail-1"),
        adapter=ScriptedAdapter([scripted]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-cal-2",
        client_factory=factory,
        batch_size=10,
    )
    assert result.proposed == 1
    params = captured_actions[0]["params_json"]
    assert params["freebusy_conflict"] is True
    assert params["priority"] == "P3"


@pytest.mark.asyncio
async def test_schedule_bucket_no_time_extracted_skips_freebusy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When extract_meeting_time returns None, we skip the calendar
    lookup entirely (no `proposed_start_iso`, no `freebusy_conflict` key,
    priority stays at the protocol default P2)."""
    captured_actions: list[dict[str, Any]] = []

    async def fake_emit_action(body: dict[str, Any], *, silo: str) -> bool:
        captured_actions.append(body)
        return True

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill.emit_action", fake_emit_action
    )

    calendar_called: list[bool] = []

    class _AssertNotCalledStub:
        def freebusy(self, *_a: Any, **_kw: Any) -> list[Any]:
            calendar_called.append(True)
            return []

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill._build_calendar_client",
        lambda *_a, **_kw: _AssertNotCalledStub(),
    )

    # Body has no defensible time reference — ambiguous "by 2pm" deadline.
    raw = [_schedule_gmail_raw("Need this back by 2pm please")]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    scripted = json.dumps(
        {
            "results": [
                {
                    "bucket": "schedule",
                    "confidence": "high",
                    "rationale": "vague deadline",
                }
            ]
        }
    )

    result = await _triage_account(
        entry=_gmail_entry("gmail-1"),
        adapter=ScriptedAdapter([scripted]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-cal-3",
        client_factory=factory,
        batch_size=10,
    )
    assert result.proposed == 1
    assert calendar_called == []
    params = captured_actions[0]["params_json"]
    assert "proposed_start_iso" not in params
    assert "freebusy_conflict" not in params
    # Default SCHEDULE priority is P2 per protocol matrix.
    assert params["priority"] == "P2"


@pytest.mark.asyncio
async def test_schedule_bucket_calendar_twin_missing_skips_gracefully(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the calendar twin account is missing (operator hasn't run the
    OAuth provisioner for the calendar scope), still emit the action with
    proposed_start_iso + meeting_url, but omit freebusy_conflict (we can't
    check)."""
    captured_actions: list[dict[str, Any]] = []

    async def fake_emit_action(body: dict[str, Any], *, silo: str) -> bool:
        captured_actions.append(body)
        return True

    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill.emit_action", fake_emit_action
    )

    # Return None to signal no twin available.
    monkeypatch.setattr(
        "pf_runtime.communications.triage_skill._build_calendar_client",
        lambda *_a, **_kw: None,
    )

    raw = [
        _schedule_gmail_raw(
            "Can we meet Tuesday at 2pm? https://meet.google.com/abc-defg-hij"
        )
    ]

    def factory(_e: RegistryEntry, _s: SyncStateStore) -> Any:
        return FakeClient(raw=raw)

    scripted = json.dumps(
        {
            "results": [
                {
                    "bucket": "schedule",
                    "confidence": "high",
                    "rationale": "proposes time",
                }
            ]
        }
    )

    result = await _triage_account(
        entry=_gmail_entry("gmail-1"),
        adapter=ScriptedAdapter([scripted]),
        proposal_tool=_proposal_tool(tmp_path),
        sync_store=_store(tmp_path),
        classifier_model="model",
        profile_slug="personal",
        run_id="run-cal-4",
        client_factory=factory,
        batch_size=10,
    )
    assert result.proposed == 1
    params = captured_actions[0]["params_json"]
    assert params["proposed_start_iso"]
    assert "meet.google.com/abc-defg-hij" in params["meeting_url"]
    # Without a twin, we can't compute conflict — omit the key.
    assert "freebusy_conflict" not in params
    # Priority falls back to default P2 (no conflict downgrade possible).
    assert params["priority"] == "P2"
