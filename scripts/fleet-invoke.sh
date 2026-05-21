#!/usr/bin/env bash
# fleet-invoke.sh — on-demand invocation of a Hermes profile's skill.
#
# Used during the data-accumulation window to fire profile runs outside the
# cron cadence. Sets the active profile via ~/.hermes/active_profile (the
# mechanism hermes_cli/profiles.py uses for profile context), then runs
# `hermes -z` non-interactive mode with the provided prompt.
#
# Routes model selection from the profile's config.yaml `model.routing` block:
#   - Looks up routing[<skill_slug_underscored>]; falls back to `model.default`.
#   - Translates `provider:model_id` (e.g. `anthropic:claude-sonnet-4-6`) to
#     `--provider <p> -m <model>` flags. Values containing `/` (e.g.
#     `nvidia/nemotron-...:free`) pass through as bare `-m <value>`, which
#     hermes routes via the profile's default provider (OpenRouter).
#   - Empty/missing routing → no model args; hermes uses its built-in default.
#
# Usage:
#   fleet-invoke.sh [--dry-run] <profile> <skill> [prompt-extras...]
#
# Examples:
#   fleet-invoke.sh marin weekly-review
#   fleet-invoke.sh --dry-run marin aeo-opportunity-scout 'topic: smoke'
#   fleet-invoke.sh quill draft-linkedin-field-note "Pillar 1 (workflow drag)"
#   fleet-invoke.sh stet critique-draft "target: _inbox/quill-drafts/<file>.md"

set -euo pipefail

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

PROFILE="${1:-}"
SKILL="${2:-}"
shift 2 2>/dev/null || true
EXTRAS="${*:-}"

if [[ -z "$PROFILE" || -z "$SKILL" ]]; then
  echo "Usage: $0 [--dry-run] <profile> <skill> [prompt-extras]" >&2
  echo "Profiles: atlas-ceo marin codex quill stet technical-operator" >&2
  exit 2
fi

HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
PROFILE_DIR="$HERMES_HOME/profiles/$PROFILE"

if [[ ! -d "$PROFILE_DIR" ]]; then
  echo "error: profile not found at $PROFILE_DIR" >&2
  exit 2
fi

# parse_routing(profile_dir, skill_slug) → prints model flags for hermes -z.
# Reads <profile_dir>/config.yaml's model.routing[skill_slug_with_underscores].
# Falls back to model.default. Empty output means "let hermes pick the default".
parse_routing() {
  local profile_dir="$1"
  local skill_slug="$2"
  local config="$profile_dir/config.yaml"
  [[ -f "$config" ]] || { echo ""; return; }
  python3 - "$config" "$skill_slug" <<'PY'
import sys
try:
    import yaml
except Exception:
    print("")
    sys.exit(0)
try:
    with open(sys.argv[1], "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
except Exception:
    print("")
    sys.exit(0)
slug = sys.argv[2].replace("-", "_")
model_cfg = cfg.get("model") or {}
routing = model_cfg.get("routing") or {}
model = routing.get(slug)
if not model:
    model = model_cfg.get("default")
if not model:
    print("")
    sys.exit(0)
# provider:model_id (e.g. anthropic:claude-sonnet-4-6) → --provider P -m M.
# Values with `/` (e.g. nvidia/nemotron-...:free) keep their full path as -m.
if ":" in model and "/" not in model:
    provider, model_id = model.split(":", 1)
    print(f"--provider {provider} -m {model_id}")
else:
    print(f"-m {model}")
PY
}

# Capture current active profile so we can restore it
PRIOR_PROFILE="$(cat "$HERMES_HOME/active_profile" 2>/dev/null || true)"
echo "$PROFILE" > "$HERMES_HOME/active_profile"
trap 'if [[ -n "$PRIOR_PROFILE" ]]; then echo "$PRIOR_PROFILE" > "$HERMES_HOME/active_profile"; fi' EXIT

MODEL_ARGS="$(parse_routing "$PROFILE_DIR" "$SKILL")"
PROMPT="Use the ${SKILL} skill from this profile. ${EXTRAS}"

if [[ -n "$DRY_RUN" ]]; then
  echo "Would run: hermes ${MODEL_ARGS} -z \"${PROMPT}\""
  exit 0
fi

# hermes -z is the non-interactive one-shot mode (v0.12 release notes).
# shellcheck disable=SC2086  # intentional word-splitting on MODEL_ARGS
hermes ${MODEL_ARGS} -z "$PROMPT"
