"""Priority computation for the operator protocol.

Bucket = WHAT the classifier thinks the message is.
Priority = WHEN Alex needs to see it.

Bucket comes from the classifier (cheap, stable, regression-protected).
Priority is a Python derivation from bucket + per-silo VIP rules + a
small set of urgency signals scanned in the subject/snippet — keeping
the classifier prompt frozen.

Levels (lower number = higher urgency):
- P0 — Now (top of lane, sticky)
- P1 — Today (lane, expanded by default)
- P2 — This week (lane, collapsed by default)
- P3 — Background (chip count)
"""

from __future__ import annotations

import re
from typing import Literal

from pf_runtime.communications.rules import SiloRules, sender_is_vip
from pf_runtime.communications.schema import NormalizedMessage, TriageBucket

Priority = Literal["P0", "P1", "P2", "P3"]


# Urgency keywords trigger a P0 escalation independent of the classifier's
# confidence. Matched case-insensitively against subject + snippet.
_URGENT_DEADLINE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(urgent|asap|deadline|past due|overdue)\b", re.I),
    re.compile(r"\b(today|by eod|end of day|by cob)\b", re.I),
    re.compile(r"\baction required\b", re.I),
    re.compile(r"\bservice will be suspended\b", re.I),
)

# Billing/compliance senders that should bump to P0 when paired with
# NEEDS_ALEX_TODAY. (Distinct from rules.yaml VIPs, which Alex tunes.)
_BILLING_LOCAL_PARTS: frozenset[str] = frozenset(
    {"billing", "accounts", "invoices", "payments", "ar", "accountsreceivable"}
)


def compute_priority(
    *,
    bucket: TriageBucket,
    msg: NormalizedMessage,
    silo_rules: SiloRules,
) -> Priority:
    """Return one of P0..P3 for the given bucket + sender + rules.

    Pure function: no I/O, no side effects, deterministic given inputs.
    Order of checks: most-urgent-first; first match wins.
    """
    sender = msg.sender or ""
    has_urgency_signal = _has_urgency_signal(msg)
    is_billing_sender = _is_billing_sender(sender)
    in_p0_vips = sender_is_vip(silo_rules, sender, tier="p0")
    in_any_vips = sender_is_vip(silo_rules, sender, tier="any")

    # P0 — Now
    if bucket is TriageBucket.NEEDS_ALEX_TODAY and (
        has_urgency_signal or in_p0_vips or is_billing_sender
    ):
        return "P0"
    if in_p0_vips:
        # P0 VIP override applies regardless of bucket (named-family-tier).
        return "P0"

    # P1 — Today
    if bucket is TriageBucket.NEEDS_ALEX_TODAY:
        return "P1"
    if bucket is TriageBucket.NEEDS_REPLY and in_any_vips:
        return "P1"

    # P2 — This week
    if bucket in (TriageBucket.NEEDS_REPLY, TriageBucket.SCHEDULE):
        return "P2"
    if bucket is TriageBucket.RELEASE_UPDATE and in_any_vips:
        return "P2"

    # P3 — Background (promotion, noise, waiting, fyi, release_update non-VIP)
    return "P3"


def _has_urgency_signal(msg: NormalizedMessage) -> bool:
    haystack = f"{msg.subject}\n{msg.snippet}"
    return any(p.search(haystack) for p in _URGENT_DEADLINE_PATTERNS)


def _is_billing_sender(sender: str) -> bool:
    if not sender or "@" not in sender:
        return False
    addr = sender.strip().lower()
    # Strip display-name wrap if present.
    if "<" in addr and ">" in addr:
        start = addr.find("<")
        end = addr.find(">", start + 1)
        if start != -1 and end != -1:
            addr = addr[start + 1 : end]
    local = addr.split("@", 1)[0]
    return local in _BILLING_LOCAL_PARTS
