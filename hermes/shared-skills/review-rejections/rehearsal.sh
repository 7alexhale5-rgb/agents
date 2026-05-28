#!/usr/bin/env bash
# review-rejections rehearsal — seeds a triage task as the calling profile,
# rejects it via the local cockpit, runs the skill's procedure, prints the
# operator-feedback block, cleans up.
#
# Doubles as the executable form of the SKILL.md procedure: when an agent's
# wake cycle invokes `review-rejections`, it can run the inner `_run()` body
# directly (skip the seed/reject/cleanup; just the read).
#
# Requires: hermes CLI on PATH, jq, curl, PFOS cockpit on 127.0.0.1:3000
# (only for the seed-reject leg — the read-only procedure has no such dep).
set -euo pipefail

if [[ -z "${HERMES_PROFILE_NAME:-}" ]]; then
  echo "[review-rejections] skipped: no \$HERMES_PROFILE_NAME" >&2
  exit 0
fi
PROFILE="$HERMES_PROFILE_NAME"

# ---------- the read-only Phase A procedure ----------
_run() {
  local now cutoff
  now=$(date +%s)
  cutoff=$((now - 30 * 86400))

  local archived
  if ! archived=$(hermes kanban list --status archived --archived --json 2>/dev/null); then
    echo "[review-rejections] hermes kanban list failed; skipping" >&2
    exit 0
  fi

  # Filter to this profile's recent rejections. jq returns task ids one per line.
  local ids
  ids=$(echo "$archived" | jq -r --arg p "$PROFILE" --argjson cutoff "$cutoff" \
    '.[] | select(.created_by == $p and .created_at >= $cutoff) | .id')

  if [[ -z "$ids" ]]; then
    echo "## Rejected pitches still worth absorbing"
    echo ""
    echo "None in the last 30 days."
    return 0
  fi

  # For each task, find the most-recent operator-cockpit comment.
  # Accumulate { id, title, ts, reason } lines tab-separated, then sort + format.
  local accum=""
  while IFS= read -r tid; do
    [[ -z "$tid" ]] && continue
    local show
    if ! show=$(hermes kanban show "$tid" --json 2>/dev/null); then
      echo "[review-rejections] hermes kanban show $tid failed; skipping that task" >&2
      continue
    fi
    local line
    line=$(echo "$show" | jq -r --arg tid "$tid" '
      . as $root
      | ($root.comments | map(select(.author == "operator-cockpit")) | sort_by(.created_at) | last) as $c
      | select($c != null)
      | [$tid, $root.task.title, ($c.created_at|tostring), $c.body] | @tsv
    ')
    [[ -n "$line" ]] && accum+="$line"$'\n'
  done <<< "$ids"

  if [[ -z "$accum" ]]; then
    echo "## Rejected pitches still worth absorbing"
    echo ""
    echo "None in the last 30 days."
    return 0
  fi

  # Sort by ts descending (most recent rejection first).
  local sorted
  sorted=$(echo -n "$accum" | sort -t$'\t' -k3,3 -nr)

  echo "## Rejected pitches still worth absorbing"
  echo ""
  echo "The cockpit operator rejected these prior pitches. Read the reasons before composing new pitches in this session. If a new pitch would repeat a recently rejected idea, either name the rejection and explain how this version addresses it, or pick a different priority."
  echo ""
  while IFS=$'\t' read -r tid title ts reason; do
    local date
    date=$(date -r "$ts" +%Y-%m-%d 2>/dev/null || echo "$ts")
    printf -- "- **%s** (\`%s\`, rejected %s)\n  Reason: \"%s\"\n\n" "$title" "$tid" "$date" "$reason"
  done <<< "$sorted"
}

# ---------- rehearsal mode (when not invoked with --read-only) ----------
if [[ "${1:-}" == "--read-only" ]]; then
  _run
  exit 0
fi

echo "=== review-rejections rehearsal under profile=$PROFILE ==="
echo ""

# Step 1 — seed a triage task created by this profile.
SEED_TITLE="REJECTION-LOOP-REHEARSAL: $(date +%H%M%S) — drop me"
SEED_REASON="rehearsal test reason — needs more sources before this is CEO-priority"
echo "[1/5] seeding triage task as created_by=$PROFILE"
SEED_JSON=$(hermes kanban create "$SEED_TITLE" \
  --body "Rehearsal pitch — should be rejected immediately." \
  --triage --created-by "$PROFILE" --json)
SEED_ID=$(echo "$SEED_JSON" | jq -r '.id')
echo "      → $SEED_ID"

# Step 2 — reject via the cockpit BFF (uses operator-cockpit author).
echo "[2/5] rejecting via cockpit POST /api/cockpit/reject"
REJECT_HTTP=$(curl -s -o /tmp/review-rejections-reject.json -w "%{http_code}" \
  -X POST http://127.0.0.1:3000/api/cockpit/reject \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg id "$SEED_ID" --arg r "$SEED_REASON" '{taskId:$id, reason:$r}')")
if [[ "$REJECT_HTTP" != "200" ]]; then
  echo "      FAIL: cockpit returned HTTP $REJECT_HTTP — body:"
  cat /tmp/review-rejections-reject.json >&2
  echo ""
  # Hard delete the seed even if reject failed.
  python3 -c "import sqlite3,os; c=sqlite3.connect(os.path.expanduser('~/.hermes/kanban.db')); c.execute('DELETE FROM task_comments WHERE task_id=?',('$SEED_ID',)); c.execute('DELETE FROM task_events WHERE task_id=?',('$SEED_ID',)); c.execute('DELETE FROM tasks WHERE id=?',('$SEED_ID',)); c.commit()"
  exit 1
fi
echo "      → 200 OK"

# Step 3 — confirm the operator-cockpit comment + archived status landed.
echo "[3/5] confirming operator-cockpit comment + archived status in DB"
STATUS=$(hermes kanban show "$SEED_ID" --json | jq -r '.task.status')
COMMENT=$(hermes kanban show "$SEED_ID" --json | jq -r '.comments[] | select(.author=="operator-cockpit") | .body' | tail -1)
echo "      status: $STATUS"
echo "      operator comment: \"$COMMENT\""
if [[ "$STATUS" != "archived" ]] || [[ "$COMMENT" != *"$SEED_REASON"* ]]; then
  echo "      FAIL: expected archived + reason verbatim"
  exit 1
fi

# Step 4 — run the skill's read-only procedure.
echo "[4/5] running the skill's read-only procedure"
echo ""
echo "---SKILL OUTPUT BEGINS---"
_run
echo "---SKILL OUTPUT ENDS---"
echo ""

# Step 5 — clean up (hard-delete via DB so re-runs are idempotent).
echo "[5/5] cleaning up seed task $SEED_ID"
python3 -c "import sqlite3,os; c=sqlite3.connect(os.path.expanduser('~/.hermes/kanban.db')); c.execute('DELETE FROM task_comments WHERE task_id=?',('$SEED_ID',)); c.execute('DELETE FROM task_events WHERE task_id=?',('$SEED_ID',)); c.execute('DELETE FROM task_links WHERE parent_id=? OR child_id=?',('$SEED_ID','$SEED_ID')); c.execute('DELETE FROM tasks WHERE id=?',('$SEED_ID',)); c.commit()"
echo "      cleaned"
echo ""
echo "=== rehearsal complete ==="
echo "If the SKILL OUTPUT block above named '$SEED_TITLE' with reason containing 'needs more sources', Phase A works."
