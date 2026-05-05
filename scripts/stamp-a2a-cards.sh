#!/usr/bin/env bash
# stamp-a2a-cards.sh — emit a2a-card.json for every profile that doesn't already have one.
# Karpathy throwaway-first: scaffold profiles get an empty side_effects[] + cost_envelope.
# Profiles can override their own card later as they activate; this is the floor.
#
# Schema produced:
#   {
#     "schema": "a2a/v1+ext",
#     "agent_id": "<name>",
#     "version": "0.1.0",
#     "description": "<from manifest .tagline or 'TBD'>",
#     "tier": <int|null>,
#     "side_effects": [],
#     "eval_suite_uri": "<inferred>",
#     "cost_envelope": { "budget_usd_per_day": 0, "alert_threshold_pct": 80 },
#     "channels": [],
#     "skills": [],
#     "stamped_at": "2026-05-05T15:01:00Z"
#   }
#
# Usage:
#   scripts/stamp-a2a-cards.sh             # stamp all profiles missing a card
#   scripts/stamp-a2a-cards.sh --force     # overwrite existing cards (use with care)

set -euo pipefail

PROFILES_DIR="${HERMES_PROFILES_DIR:-$HOME/Projects/agents/hermes/profiles}"
MARKETPLACE_DIR="${MARKETPLACE_DIR:-$HOME/Projects/agents/marketplace/manifests}"
FORCE="${1:-}"
STAMPED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

stamped=0
skipped=0

for dir in "$PROFILES_DIR"/*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  card="$dir/a2a-card.json"

  if [ -f "$card" ] && [ "$FORCE" != "--force" ]; then
    echo "skip: $name (a2a-card.json exists; use --force to overwrite)"
    skipped=$((skipped + 1))
    continue
  fi

  manifest="$dir/manifest.json"
  description="TBD"
  tier='null'
  channels='[]'
  if [ -f "$manifest" ]; then
    description=$(jq -r '.tagline // .description // "TBD"' "$manifest" 2>/dev/null || echo "TBD")
    tier=$(jq -r '.tier' "$manifest" 2>/dev/null || echo 'null')
    case "$tier" in
      ''|null|TBD) tier='null' ;;
      *) [ "$tier" -eq "$tier" ] 2>/dev/null || tier='null' ;;
    esac
    channels=$(jq -c '.channels // []' "$manifest" 2>/dev/null || echo '[]')
  fi

  # Marketplace eval-suite URI (relative to repo root)
  eval_suite_uri='null'
  if [ -d "$MARKETPLACE_DIR/$name/eval-suite" ]; then
    eval_suite_uri="\"marketplace/manifests/$name/eval-suite/\""
  fi

  jq -n \
    --arg id "$name" \
    --arg desc "$description" \
    --argjson tier "$tier" \
    --argjson channels "$channels" \
    --argjson eval_uri "$eval_suite_uri" \
    --arg stamped "$STAMPED_AT" \
    '{
      schema: "a2a/v1+ext",
      agent_id: $id,
      version: "0.1.0",
      description: $desc,
      tier: $tier,
      side_effects: [],
      eval_suite_uri: $eval_uri,
      cost_envelope: { budget_usd_per_day: 0, alert_threshold_pct: 80 },
      channels: $channels,
      skills: [],
      stamped_at: $stamped
    }' > "$card"

  echo "stamped: $name"
  stamped=$((stamped + 1))
done

echo "----"
echo "stamped: $stamped · skipped: $skipped"
