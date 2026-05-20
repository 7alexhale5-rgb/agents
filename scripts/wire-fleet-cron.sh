#!/usr/bin/env bash
# wire-fleet-cron.sh — idempotently register all PrettyFly fleet cron jobs.
#
# Uses Hermes's cronjob_tool Python API directly (not the chat slash command),
# so this is scriptable + idempotent. Jobs are stored in ~/.hermes/cron/jobs.json.
#
# Per-profile context: cronjob_tool accepts `workdir` which sets the working
# dir for the cron tick. Combined with `skill` (the named skill in that
# profile's skills/ dir), the tick has full profile context.
#
# Idempotency: cronjob action=create returns an error if the name already
# exists; we treat that as success (job already registered).
#
# DRY-RUN: pass --dry-run to print what would be created without writing.

set -euo pipefail

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
AGENTS_ROOT="${AGENTS_ROOT:-$HOME/Projects/agents}"
DRY_RUN=""
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN="--dry-run"

create_cron_job() {
  local name="$1"
  local schedule="$2"
  local prompt="$3"
  local profile="${4:-}"
  local skill="${5:-}"

  local workdir=""
  [[ -n "$profile" ]] && workdir="$HERMES_HOME/profiles/$profile"

  cd "$HERMES_HOME/hermes-agent" 2>/dev/null || cd "$AGENTS_ROOT"
  HERMES_HOME="$HERMES_HOME" "$HERMES_HOME/hermes-agent/venv/bin/python3" <<PYEOF
import sys
sys.path.insert(0, "$HERMES_HOME/hermes-agent")
from tools.cronjob_tools import cronjob
import json

kwargs = {
    "action": "create",
    "name": "$name",
    "schedule": "$schedule",
    "prompt": """$prompt""",
}
if "$skill":
    kwargs["skill"] = "$skill"
if "$workdir":
    kwargs["workdir"] = "$workdir"

if "$DRY_RUN":
    print(f"DRY-RUN: {json.dumps(kwargs, indent=2)}")
else:
    try:
        result = cronjob(**kwargs)
        print(result)
    except Exception as exc:
        # Idempotent: if job already exists, treat as success
        if "already exists" in str(exc).lower() or "duplicate" in str(exc).lower():
            print(f"OK (already registered): $name")
        else:
            raise
PYEOF
}

echo "=== Wiring PrettyFly fleet cron jobs ==="

# Atlas: weekly CEO brief (Sundays 7am for Monday read)
create_cron_job \
  "atlas-weekly-ceo-brief" \
  "0 7 * * 0" \
  "Produce the weekly CEO brief for this week. Use the latest fleet.snapshot and business.scorecard.snapshot. Write to the workspace. Follow weekly-ceo-brief skill format. After landing, emit atlas.action.proposed per the skill emission step." \
  "atlas-ceo" \
  "weekly-ceo-brief"

# Marin: weekly marketing readout (Mondays 8am)
create_cron_job \
  "marin-weekly-review" \
  "0 8 * * 1" \
  "Run weekly-review against current marketing-vault state. Produce weekly decision readout. Write to ~/Projects/marketing/_inbox/marin-readouts/. Emit marin.weekly_decision.proposed." \
  "marin" \
  "weekly-review"

# Quill: Field Note drafts (Tue + Thu 9am)
create_cron_job \
  "quill-field-note-tue" \
  "0 9 * * 2" \
  "Run draft-linkedin-field-note for the WORKS Review public signal sprint. Pick Pillar 1 (Workflow Drag) or Pillar 2 (AI Operations Audits). Produce one draft, write to ~/Projects/marketing/_inbox/quill-drafts/, emit quill.draft.proposed." \
  "quill" \
  "draft-linkedin-field-note"

create_cron_job \
  "quill-field-note-thu" \
  "0 9 * * 4" \
  "Run draft-linkedin-field-note. Pick a content pillar that was NOT used Tuesday this week. Produce one draft, write to ~/Projects/marketing/_inbox/quill-drafts/, emit quill.draft.proposed." \
  "quill" \
  "draft-linkedin-field-note"

# Stet: critique-on-land polling (every 30 min)
create_cron_job \
  "stet-critique-on-land" \
  "*/30 * * * *" \
  "Check ~/Projects/marketing/_inbox/quill-drafts/ for files newer than 30 minutes that lack a matching critique in ~/Projects/marketing/_inbox/stet-critiques/. For each, run critique-draft, emit stet.critique.proposed. Exit silently if no new drafts." \
  "stet" \
  "critique-draft"

# Fleet: daily verify-event-contract heartbeat (noon)
create_cron_job \
  "fleet-contract-heartbeat" \
  "0 12 * * *" \
  "Run python3 $AGENTS_ROOT/scripts/verify-event-contract.py --all. If any contract violation appears, emit hermes.contract.violation event with details. If all clean, emit hermes.contract.verified event."

# Fleet: autonomy-gate watcher (every 30 min)
create_cron_job \
  "fleet-autonomy-gate-watcher" \
  "*/30 * * * *" \
  "Run bash $AGENTS_ROOT/scripts/check-autonomy-gates.sh. The script queries agent_events, evaluates counter-based gates per profile, and emits <profile>.autonomy.graduated events when thresholds clear."

# Per-profile self-audits (Sundays 6am — staggered 5 min apart)
create_cron_job \
  "marin-self-audit" \
  "0 6 * * 0" \
  "Run self-audit. Run promptfoo eval, sample last 7 days of readouts, write evidence, emit marin.weekly_decision.proposed with audit_type=self in data." \
  "marin" \
  "self-audit"

create_cron_job \
  "quill-self-audit" \
  "5 6 * * 0" \
  "Run self-audit per the skill." \
  "quill" \
  "self-audit"

create_cron_job \
  "stet-self-audit" \
  "10 6 * * 0" \
  "Run self-audit per the skill." \
  "stet" \
  "self-audit"

create_cron_job \
  "atlas-self-audit" \
  "15 6 * * 0" \
  "Run self-audit per the skill." \
  "atlas-ceo" \
  "self-audit"

# Inbox aging (daily 3am)
create_cron_job \
  "marketing-inbox-archive" \
  "0 3 * * *" \
  "Run bash $AGENTS_ROOT/scripts/inbox-archive.sh. Archives marketing-vault inbox files older than 14 days. Flags approved-but-unpromoted files."

echo ""
echo "=== Done. Verify with: ==="
echo "  python3 -c \"import sys; sys.path.insert(0, '$HERMES_HOME/hermes-agent'); from tools.cronjob_tools import cronjob; print(cronjob(action='list'))\""
