#!/usr/bin/env bash
# fleet-invoke.sh — on-demand invocation of a Hermes profile's skill.
#
# Used during the data-accumulation window to fire profile runs outside the
# cron cadence. Sets the active profile via ~/.hermes/active_profile (the
# mechanism hermes_cli/profiles.py uses for profile context), then runs
# `hermes -z` non-interactive mode with the provided prompt.
#
# Usage:
#   fleet-invoke.sh <profile> <skill> [prompt-extras...]
#
# Examples:
#   fleet-invoke.sh cmo weekly-review
#   fleet-invoke.sh quill draft-linkedin-field-note "Pillar 1 (workflow drag)"
#   fleet-invoke.sh stet critique-draft "target: _inbox/quill-drafts/<file>.md"

set -euo pipefail

PROFILE="${1:-}"
SKILL="${2:-}"
shift 2 2>/dev/null || true
EXTRAS="${*:-}"

if [[ -z "$PROFILE" || -z "$SKILL" ]]; then
  echo "Usage: $0 <profile> <skill> [prompt-extras]" >&2
  echo "Profiles: atlas-ceo cmo codex quill stet" >&2
  exit 2
fi

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PROFILE_DIR="$HERMES_HOME/profiles/$PROFILE"

if [[ ! -d "$PROFILE_DIR" ]]; then
  echo "error: profile not found at $PROFILE_DIR" >&2
  exit 2
fi

# Capture current active profile so we can restore it
PRIOR_PROFILE="$(cat "$HERMES_HOME/active_profile" 2>/dev/null || true)"
echo "$PROFILE" > "$HERMES_HOME/active_profile"
trap 'if [[ -n "$PRIOR_PROFILE" ]]; then echo "$PRIOR_PROFILE" > "$HERMES_HOME/active_profile"; fi' EXIT

PROMPT="Use the ${SKILL} skill from this profile. ${EXTRAS}"

# hermes -z is the non-interactive one-shot mode (v0.12 release notes).
hermes -z "$PROMPT"
