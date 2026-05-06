#!/usr/bin/env bash
# Hermes feature audit — Phase 4.7 pre-work item E (Gate G2).
# Catalogs which Hermes features each of the 13 profiles actually uses today,
# so PF Runtime sub-phase 4.7.2 ships only what's in-use.
#
# Output: HERMES_FEATURE_USAGE.md at .planning/phase-4-7-prettyfly-runtime/feature-usage/

set -euo pipefail

HERMES_RUNTIME="$HOME/.hermes"
PROFILES_DIR="$HERMES_RUNTIME/profiles"
SESSIONS_DIR="$HERMES_RUNTIME/sessions"
OUT_DIR="$HOME/Projects/agents/.planning/phase-4-7-prettyfly-runtime/feature-usage"
OUT_FILE="${1:-$OUT_DIR/HERMES_FEATURE_USAGE.md}"

mkdir -p "$(dirname "$OUT_FILE")"

# Profile slugs we care about (from ADR-001)
PROFILES=(personal mobile codex lawdbot consultops sportsbook yeh-ops atlas-ceo viper-outreach quill-content forge-audit ops vanclief)

# Hermes features to audit
declare -a FEATURES=(
    "memory_tool:Built-in MEMORY.md/USER.md persistent stores"
    "skill_manager_tool:Skill creation/deletion/metadata"
    "kanban_tools:Multi-agent task board (v0.12)"
    "honcho_provider:Honcho dialectic memory plugin"
    "voice_loop:Voice transcription pipeline"
    "image_generation:Image gen routing"
    "tinker_atropos:Per-tenant LoRA"
    "dream_loop:Post-session reflection"
)

cat > "$OUT_FILE" <<EOF
# Hermes feature usage audit — $(date +%Y-%m-%d)

> **Phase 4.7 Gate G2.** PF Runtime sub-phase 4.7.2 ships only features where in-use=yes for ≥1 profile.

## Method

- **Phase 1 (this run):** grep profile config files + check skills/ + check rooms/voice/ at \`$PROFILES_DIR/<slug>/\`. This captures *static* feature enablement (does the profile reference a feature in its config), not *actual usage*.
- **Phase 2 (deferred):** SQLite session DB inspection at \`$SESSIONS_DIR/\` for runtime tool-call counts, plus Langfuse trace queries for 80th-percentile-used tools per profile over 30 days. This captures *real usage*.
- G2 (per PLAN.md §1) requires both phases. Phase 1 evidence below is sufficient to scope which features are *referenced* in profile configs; feature-scoping decisions for sub-phase 4.7.2 (which features PF Runtime ships) require Phase 2 evidence and remain blocked on it.

## Per-profile feature matrix

| Profile | memory_tool | skill_manager | kanban_tools | honcho | voice_loop | image_gen | tinker_atropos | dream_loop |
|---------|-------------|---------------|--------------|--------|------------|-----------|----------------|------------|
EOF

for profile in "${PROFILES[@]}"; do
    profile_dir="$PROFILES_DIR/$profile"
    line="| $profile |"

    if [ ! -d "$profile_dir" ]; then
        # Profile dir missing in runtime mirror
        for _ in "${FEATURES[@]}"; do
            line+=" — |"
        done
        echo "$line" >> "$OUT_FILE"
        continue
    fi

    # memory_tool: presence of MEMORY.md > 0 bytes + memory_tool in config
    if [ -s "$profile_dir/MEMORY.md" ] && grep -qE "memory[_-]tool|memory_tool" "$profile_dir/config.yaml" 2>/dev/null; then
        line+=" Y |"
    elif [ -s "$profile_dir/MEMORY.md" ]; then
        line+=" implicit |"
    else
        line+=" N |"
    fi

    # skill_manager_tool: skills/ dir non-empty
    # Note: `find` on a missing dir returns non-zero; with `set -e` + `pipefail`
    # that propagates through `$( ... )` and silently exits the loop. Guard
    # explicitly so all 13 profile rows render even when the dir is absent.
    if [ -d "$profile_dir/skills" ]; then
        skill_count=$(find "$profile_dir/skills" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')
    else
        skill_count=0
    fi
    if [ "$skill_count" -gt 0 ]; then
        line+=" Y ($skill_count) |"
    else
        line+=" N |"
    fi

    # kanban_tools: HERMES_KANBAN_BOARD configured
    if grep -qE "kanban|HERMES_KANBAN" "$profile_dir/config.yaml" "$profile_dir/.env" 2>/dev/null; then
        line+=" Y |"
    else
        line+=" N |"
    fi

    # honcho: provider == honcho
    if grep -qE "memory_provider:.*honcho|honcho_workspace" "$profile_dir/config.yaml" 2>/dev/null; then
        line+=" Y |"
    else
        line+=" N |"
    fi

    # voice_loop: voice in config or rooms/voice/
    if [ -d "$profile_dir/rooms/voice" ] || grep -qE "voice|whisper|tts" "$profile_dir/config.yaml" 2>/dev/null; then
        line+=" Y |"
    else
        line+=" N |"
    fi

    # image_gen: image_routing or image_gen toolset
    if grep -qE "image_gen|image_routing|imagen" "$profile_dir/config.yaml" 2>/dev/null; then
        line+=" Y |"
    else
        line+=" N |"
    fi

    # tinker_atropos: lora or fine_tune in config
    if grep -qE "tinker|atropos|lora|fine_tune" "$profile_dir/config.yaml" 2>/dev/null; then
        line+=" Y |"
    else
        line+=" N |"
    fi

    # dream_loop: dream or compaction enabled
    if grep -qE "dream|compaction|reflect" "$profile_dir/config.yaml" 2>/dev/null; then
        line+=" Y |"
    else
        line+=" N |"
    fi

    echo "$line" >> "$OUT_FILE"
done

cat >> "$OUT_FILE" <<EOF

## Aggregate (in-use across fleet)

EOF

for feat_def in "${FEATURES[@]}"; do
    feat="${feat_def%%:*}"
    desc="${feat_def#*:}"
    # Count profiles using it (rough — Y or implicit in matrix)
    used=$(grep -c " Y " "$OUT_FILE" 2>/dev/null || echo 0)
    echo "- **$feat** ($desc): see matrix above" >> "$OUT_FILE"
done

cat >> "$OUT_FILE" <<EOF

## Phase 4.7 implications

| If any profile uses it... | PF Runtime ships it in sub-phase 4.7.2 |
|---------------------------|----------------------------------------|
| memory_tool | Yes — Tier 2 buffer + MEMORY.md mutator |
| skill_manager | Yes — agentskills.io progressive-disclosure loader (Tier 4) |
| kanban_tools | Yes — Postgres-backed Kanban (4.7.4) |
| honcho | Server-side via MCP (no PF Runtime code; Honcho server stays AGPL) |
| voice_loop | Optional 4.7.3.B (Slack \`file_shared\` audio events) |
| image_gen | Pass-through to LiteLLM image routing — no PF Runtime code needed |
| tinker_atropos | Out of scope for 4.7; deferred to per-tenant LoRA SKU |
| dream_loop | Yes — \`pf-runtime/dream/post_session.py\` (4.7.2) |

## Action

Operator reviews matrix; flags any "in-use but not in 4.7 scope" surprises.
EOF

echo "Feature audit written to: $OUT_FILE"
