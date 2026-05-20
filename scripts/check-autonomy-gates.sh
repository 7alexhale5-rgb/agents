#!/usr/bin/env bash
# check-autonomy-gates.sh — counter-based autonomy-gate evaluator.
#
# For each profile + each gate, queries agent_events, counts approvals,
# compares against threshold, prints current state. When a gate's
# threshold is crossed AND no graduation event has fired yet, emits
# <profile>.autonomy.graduated event so downstream skills can key off
# config-as-data (not config-as-code-flag).
#
# Run every 30 min via Hermes cron (fleet-autonomy-gate-watcher).
#
# Gate definitions are inline below — config-as-data. To add a new gate,
# append a new GATE_* block.

set -euo pipefail

AGENTS_ROOT="${AGENTS_ROOT:-$HOME/Projects/agents}"
PFOS_ROOT="${PFOS_ROOT:-$HOME/Projects/prettyfly-os}"

# Source the agent_events token + URL for emit-agent-event.py
if [[ -f "$HOME/.config/prettyfly-marketing/hermes-tokens.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$HOME/.config/prettyfly-marketing/hermes-tokens.env"
  set +a
fi

# Helper: query PFOS via supabase, return count.
# Usage: query_count "<SQL fragment after FROM agent_events>"
query_count() {
  local where="$1"
  cd "$PFOS_ROOT"
  local q="SELECT count(*) FROM public.agent_events WHERE $where;"
  echo "$q" | supabase db query --linked 2>/dev/null \
    | grep -o '"count": [0-9]*' \
    | grep -o '[0-9]*' \
    || echo "0"
}

# Helper: check whether a graduation event has already fired for this gate.
graduation_fired() {
  local event_type="$1"
  local cnt
  cnt="$(query_count "type = '$event_type'")"
  [[ "${cnt:-0}" -gt 0 ]]
}

# Helper: emit a graduation event.
emit_graduation() {
  local profile="$1"
  local gate_name="$2"
  local event_type="$3"
  local detail_json="$4"

  cd "$AGENTS_ROOT"
  python3 scripts/emit-agent-event.py \
    --profile "$profile" \
    --tool "$(graduation_tool_for "$profile")" \
    --extra-json "{\"gate_name\":\"$gate_name\",\"graduated_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"detail\":$detail_json}" \
    || echo "WARN: graduation emit failed for $profile/$gate_name"
}

# Each profile's "default emission tool" (used for graduation events too —
# we reuse existing tool contracts rather than declaring new ones).
graduation_tool_for() {
  case "$1" in
    marin) echo "weekly_decision.propose" ;;
    quill) echo "draft_field_note.propose" ;;
    stet) echo "critique_draft.propose" ;;
    atlas-ceo) echo "atlas.propose_action" ;;
    *) echo "" ;;
  esac
}

echo "=== Autonomy gate state — $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# ---- Gate: marin.confidence_auto_approve ----
# 5 consecutive approved marin.weekly_decision.proposed events, 0 critical failures
GATE_NAME="marin.confidence_auto_approve"
GRADUATION_EVENT="marin.autonomy.graduated"
APPROVALS="$(query_count "type='marin.weekly_decision.proposed' AND status='approved' AND data->>'audit_type' IS NULL")"
FAILURES="$(query_count "type='marin.weekly_decision.proposed' AND status='rejected' AND created_at > NOW() - INTERVAL '30 days'")"
echo "$GATE_NAME: $APPROVALS/5 approvals, $FAILURES/0 failures"
if [[ "$APPROVALS" -ge 5 && "$FAILURES" -eq 0 ]]; then
  if graduation_fired "$GRADUATION_EVENT"; then
    echo "  already graduated"
  else
    echo "  → GRADUATING"
    emit_graduation "marin" "$GATE_NAME" "$GRADUATION_EVENT" "{\"approvals\":$APPROVALS,\"failures\":$FAILURES}"
  fi
fi

# ---- Gate: stet.auto_routing ----
# 10 critiques routed + ≥80% Alex-verdict-agreement (i.e. ≤2 'rejected' in last 10)
GATE_NAME="stet.auto_routing"
GRADUATION_EVENT="stet.autonomy.graduated"
CRITIQUES="$(query_count "type='stet.critique.proposed' AND data->>'audit_type' IS NULL")"
REJECTIONS="$(query_count "type='stet.critique.proposed' AND status='rejected' AND created_at > NOW() - INTERVAL '60 days'")"
echo "$GATE_NAME: $CRITIQUES/10 critiques, $REJECTIONS/2 rejections"
if [[ "$CRITIQUES" -ge 10 && "$REJECTIONS" -le 2 ]]; then
  if graduation_fired "$GRADUATION_EVENT"; then
    echo "  already graduated"
  else
    echo "  → GRADUATING"
    emit_graduation "stet" "$GATE_NAME" "$GRADUATION_EVENT" "{\"critiques\":$CRITIQUES,\"rejections\":$REJECTIONS}"
  fi
fi

# ---- Gate: quill.consistent_quality ----
# 8 approved drafts + ≥75% Alex-approval (i.e. ≤2 'rejected' in last 8)
GATE_NAME="quill.consistent_quality"
GRADUATION_EVENT="quill.autonomy.graduated"
DRAFTS="$(query_count "type='quill.draft.proposed' AND status='approved' AND data->>'audit_type' IS NULL")"
DRAFT_REJ="$(query_count "type='quill.draft.proposed' AND status='rejected' AND created_at > NOW() - INTERVAL '45 days'")"
echo "$GATE_NAME: $DRAFTS/8 approvals, $DRAFT_REJ/2 rejections"
if [[ "$DRAFTS" -ge 8 && "$DRAFT_REJ" -le 2 ]]; then
  if graduation_fired "$GRADUATION_EVENT"; then
    echo "  already graduated"
  else
    echo "  → GRADUATING"
    emit_graduation "quill" "$GATE_NAME" "$GRADUATION_EVENT" "{\"drafts\":$DRAFTS,\"rejections\":$DRAFT_REJ}"
  fi
fi

# ---- Gate: atlas.advisor_trusted ----
# 6 approved CEO actions + 0 critical failures
GATE_NAME="atlas.advisor_trusted"
GRADUATION_EVENT="atlas.autonomy.graduated"
ACTIONS="$(query_count "type='atlas.action.proposed' AND status='approved' AND data->>'audit_type' IS NULL")"
ACTION_REJ="$(query_count "type='atlas.action.proposed' AND status='rejected' AND created_at > NOW() - INTERVAL '60 days'")"
echo "$GATE_NAME: $ACTIONS/6 approvals, $ACTION_REJ/0 rejections"
if [[ "$ACTIONS" -ge 6 && "$ACTION_REJ" -eq 0 ]]; then
  if graduation_fired "$GRADUATION_EVENT"; then
    echo "  already graduated"
  else
    echo "  → GRADUATING"
    emit_graduation "atlas-ceo" "$GATE_NAME" "$GRADUATION_EVENT" "{\"actions\":$ACTIONS,\"rejections\":$ACTION_REJ}"
  fi
fi

echo "=== Done ==="
