"""Filing-label suggestion for the operator protocol.

Returns the `<SILO>/<role>` label that PFOS shows as the suggested
file destination on each Needs you card. V1 emits this as
``params_json.label_suggestion`` on the `inbox.label` agent_action;
nothing is applied to Gmail/Graph until v2 lifts the mutation gate.

The role is derived from:
1. Per-silo `role_hints` matches in triage-rules.yaml (first-match-wins)
2. Bucket-driven defaults when no rule hint fires (e.g. PROMOTION → Newsletters)
3. ``None`` when neither matches — the agent_action carries no label
   suggestion and Alex sees just the bucket badge.
"""

from __future__ import annotations

from pf_runtime.communications.rules import SiloRules, first_role_match
from pf_runtime.communications.schema import NormalizedMessage, TriageBucket

_SILO_PREFIX: dict[str, str] = {
    "koho": "KOHO",
    "ctox": "CTOX",
    "yeh": "YEH",
    "prettyfly": "PF",
}


# Bucket-driven fallback when no role_hint matches. Keeps the lane
# consistent: every PROMOTION lands under <SILO>/Newsletters, every
# NOISE under <SILO>/Archive, etc.
_BUCKET_DEFAULT_SUFFIX: dict[TriageBucket, str] = {
    TriageBucket.PROMOTION: "Newsletters",
    TriageBucket.NOISE: "Archive",
    TriageBucket.FYI: "Reference",
    TriageBucket.WAITING: "Waiting",
    TriageBucket.RELEASE_UPDATE: "Updates",
}


def suggest_label(
    *,
    silo: str,
    bucket: TriageBucket,
    msg: NormalizedMessage,
    silo_rules: SiloRules,
) -> str | None:
    """Return ``<SILO>/<role>`` or ``None`` if nothing should be suggested.

    Lookup order:
    1. Match against ``silo_rules.role_hints`` (first match wins).
    2. Bucket default for PROMOTION/NOISE/FYI/WAITING/RELEASE_UPDATE.
    3. ``None`` — no suggestion (NEEDS_ALEX_TODAY / NEEDS_REPLY / SCHEDULE
       without a hint match stay unfiled by default; the operator can
       add a hint to file them).
    """
    prefix = _SILO_PREFIX.get(silo)
    if prefix is None:
        # Unknown silo (home/fleet/skills/ops in writeback enum but
        # never targets for the personal triage flow). Return None
        # rather than synthesise a label PFOS would treat as garbage.
        return None

    sender = msg.sender or ""
    role_from_hint = first_role_match(silo_rules.role_hints, sender)
    if role_from_hint:
        return f"{prefix}/{role_from_hint}"

    default_suffix = _BUCKET_DEFAULT_SUFFIX.get(bucket)
    if default_suffix:
        return f"{prefix}/{default_suffix}"

    return None
