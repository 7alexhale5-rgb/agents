#!/usr/bin/env bash
# bootstrap-profile.sh — scaffold a new profile in the versioned tree
#
# Usage: bootstrap-profile.sh <profile-name>
#
# Creates ~/Projects/agents/hermes/profiles/<name>/ with the standard sub-tree.
# Does NOT create the Hermes runtime dir — run `hermes profile create <name>` separately.

set -euo pipefail

NAME="${1:-}"
if [ -z "$NAME" ]; then
  echo "usage: bootstrap-profile.sh <profile-name>" >&2
  exit 1
fi

# Validate kebab-case (profile names must match Alex's filesystem protocol)
if ! echo "$NAME" | grep -Eq '^[a-z][a-z0-9-]*[a-z0-9]$'; then
  echo "error: profile name must be kebab-case (lowercase, hyphens, no leading/trailing hyphen)" >&2
  exit 2
fi

P="$HOME/Projects/agents/hermes/profiles/$NAME"

if [ -d "$P" ]; then
  echo "error: profile already exists at $P" >&2
  exit 3
fi

echo "scaffolding profile: $NAME"
mkdir -p "$P"/{rooms,skills,workspace,scratch,memory/trajectories,eval}

cat > "$P/CLAUDE.md" <<EOF
# CLAUDE.md — \`$NAME\` profile

> **Profile:** $NAME · **Tier:** TBD · **Channels:** TBD
> **Phase:** TBD

You're inside the $NAME profile. Persona in \`SOUL.md\`, user in \`USER.md\`, memory in \`MEMORY.md\`.

## Per-task routing

| Task | Read | Skills |
|------|------|--------|
| TBD  | TBD  | TBD    |

## Model routing

TBD — fill in default / drafting / reasoning / strategic per the org standard.

## Hard rules

1. (per-profile guardrails)

## Acceptance gate

(per-profile success criterion)
EOF

cat > "$P/SOUL.md" <<EOF
# SOUL — $NAME

You are the $NAME agent. Your single job is TBD.

## Voice

Direct. Plain English. Short. Calibrated. Honest about uncertainty.

## What you handle

TBD

## What you NEVER do

- Auto-send to humans without explicit approval
- Touch money-flowing pipelines without operator authorization
- Modify other profiles' files
EOF

cat > "$P/USER.md" <<EOF
# USER — for $NAME profile

(Populate via interview-context-builder skill on first run.)
EOF

cat > "$P/MEMORY.md" <<EOF
# MEMORY — $NAME

This is the agent's narrative working memory. Append-curated, not append-only.

## Recent anchors

(Populated as the agent runs.)
EOF

cat > "$P/manifest.json" <<EOF
{
  "sku": "$NAME",
  "name": "TBD",
  "version": "0.1.0",
  "category": "TBD",
  "department": "TBD",
  "tagline": "TBD",
  "tier": "TBD",
  "depends_on": [],
  "channels": [],
  "memory_axes": ["working", "episodic", "procedural"],
  "guardrails": ["outbound_human_approval", "pii_redaction"],
  "sla": { "uptime": 99.0, "p95_latency_seconds": 30 },
  "publish": false,
  "internal_only": true
}
EOF

cat > "$P/config.yaml" <<EOF
profile: $NAME

agent:
  max_iterations: 32
  iteration_budget_tokens: 200000

model:
  default_provider: openrouter
  default_model: nvidia/nemotron-nano-9b-v2

memory:
  built_in:
    enabled: true
    fts5_enabled: true
  honcho:
    enabled: false

mcp_servers: {}
skills:
  install: []
channels: {}
approval:
  mode: explicit_for_outbound
guardrails:
  spend_cap_per_day_usd: 5
  alert_threshold_pct: 80
EOF

cat > "$P/pricing.yaml" <<EOF
internal_only: true
billable_to_alex: false
hypothetical_external_tiers:
  starter: { monthly_price: 49, actions_per_day: 50 }
  pro:     { monthly_price: 199, actions_per_day: 500 }
  scale:   { monthly_price: 999, actions_per_day: unlimited }
byok_keys: []
EOF

cat > "$P/.env.example" <<EOF
# Per-profile env overrides. Copy to .env and fill in.
# (Real .env is gitignored per FILESYSTEM-PROTOCOL.)
EOF

cat > "$P/PAUSED.template" <<EOF
This is the kill-switch template. Rename to \`PAUSED\` (no extension) to halt this profile's runtime.
\`hermes\` will refuse to invoke any skill on this profile while \`PAUSED\` exists.
EOF

cat > "$P/changelog.md" <<EOF
# Changelog — $NAME profile

## $(date +%Y-%m-%d) — initial scaffold

- Created via \`scripts/bootstrap-profile.sh $NAME\`
EOF

ln -s CLAUDE.md "$P/AGENTS.md"
touch "$P/memory/honcho-link.yaml"
touch "$P/eval/promptfoo.yaml"

echo "done."
echo "next:"
echo "  1. fill in SOUL.md / USER.md / manifest.json / config.yaml"
echo "  2. add skills under skills/<name>/SKILL.md"
echo "  3. \`hermes profile create $NAME\` to create runtime mirror"
echo "  4. \`scripts/sync-profile.sh push $NAME\` to push versioned → runtime"
