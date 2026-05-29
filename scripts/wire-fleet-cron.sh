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
    # Real idempotency: cronjob(action='create') does NOT error on a duplicate
    # name — it appends a second job. So we must check existence ourselves and
    # skip the create when a job of this name already exists. (Without this
    # guard, every re-run of this script silently doubles every job.)
    #
    # We read the global store file directly rather than cronjob(action='list'),
    # because list is ORIGIN-SCOPED: it only returns jobs created in the current
    # session context, so it cannot see jobs registered by earlier sessions and
    # the guard would wrongly re-create them.
    import os
    names = set()
    store_path = os.path.join("$HERMES_HOME", "cron", "jobs.json")
    if os.path.exists(store_path):
        with open(store_path) as fh:
            store = json.load(fh)
        for j in store.get("jobs", []):
            if isinstance(j, dict) and j.get("name"):
                names.add(j["name"])
    if "$name" in names:
        print(f"OK (already registered): $name")
    else:
        result = cronjob(**kwargs)
        print(result)
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

# hermes-scout: weekly Hermes-runtime topic sweep (Saturdays 6am)
create_cron_job \
  "hermes-scout-weekly-sweep" \
  "0 6 * * 6" \
  "Run topic-sweep per the skill. Check notebooklm auth liveness, sweep the Hermes-runtime sources via /research-stack --deep --youtube --vault --notebook 771c0174 since the last digest, dedup against the capability roadmap + prior digests, write a CI-rubric-verdict digest to ~/Projects/agents/_inbox/hermes-scout/, ingest sources into notebook 771c0174, emit hermes_scout.digest.proposed." \
  "hermes-scout" \
  "topic-sweep"

# cc-scout: weekly Claude Code + Anthropic topic sweep (Saturdays 6:05am)
create_cron_job \
  "cc-scout-weekly-sweep" \
  "5 6 * * 6" \
  "Run topic-sweep per the skill. Check notebooklm auth liveness, sweep the Claude Code + Anthropic sources via /research-stack --deep --youtube --vault --notebook 988d6e87 since the last digest, dedup against the env-global config (~/.claude/) + prior digests, write a CI-rubric-verdict digest to ~/Projects/agents/_inbox/cc-scout/, ingest sources into notebook 988d6e87, emit cc_scout.digest.proposed." \
  "cc-scout" \
  "topic-sweep"

# mcp-scout: weekly agentic-patterns + MCP topic sweep (Saturdays 6:10am)
create_cron_job \
  "mcp-scout-weekly-sweep" \
  "10 6 * * 6" \
  "Run topic-sweep per the skill. Check notebooklm auth liveness, sweep the agentic-patterns + MCP sources via /research-stack --deep --youtube --vault --notebook a4ca2b00 since the last digest, dedup against the fleet contracts (_meta/decisions/ + .mcp.json) + prior digests, write a CI-rubric-verdict digest to ~/Projects/agents/_inbox/mcp-scout/, ingest sources into notebook a4ca2b00, emit mcp_scout.digest.proposed." \
  "mcp-scout" \
  "topic-sweep"

# pkm-scout: weekly NotebookLM + PKM topic sweep (Saturdays 6:15am)
create_cron_job \
  "pkm-scout-weekly-sweep" \
  "15 6 * * 6" \
  "Run topic-sweep per the skill. Check notebooklm auth liveness, sweep the NotebookLM + PKM sources via /research-stack --deep --youtube --vault --notebook f181b42e since the last digest, dedup against the memory-vault wiki + prior digests, write a CI-rubric-verdict digest to ~/Projects/agents/_inbox/pkm-scout/, ingest sources into notebook f181b42e, emit pkm_scout.digest.proposed. A recurring notebooklm auth failure is itself a reportable finding." \
  "pkm-scout" \
  "topic-sweep"

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
