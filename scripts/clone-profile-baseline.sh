#!/usr/bin/env bash
# clone-profile-baseline.sh — provision a shadow workspace for G1 / G3 baseline runs.
#
# Usage: clone-profile-baseline.sh <source-profile> <target-baseline>
#
# Idempotent: re-running with the same args is a no-op (skip if target dirs exist).
#
# Does:
#   1. Copy versioned source → versioned target (hermes/profiles/)
#   2. Copy runtime  source → runtime  target (~/.hermes/profiles/)
#   3. Rewrite target manifest.json `sku` to match target name
#   4. Run scripts/validate-profile.sh against the target
#
# Defers (manual — needs auth tokens):
#   - LiteLLM key alias mint     → prints the curl command to run
#   - Langfuse project tag mint  → prints the curl command to run
#
# Reference: .planning/post-phase-4-7-0/NEXT_PHASE_PLAN.md §5.2.

set -euo pipefail

SRC="${1:-}"
DST="${2:-}"

if [ -z "$SRC" ] || [ -z "$DST" ]; then
  echo "usage: clone-profile-baseline.sh <source-profile> <target-baseline>" >&2
  exit 1
fi

if ! echo "$DST" | grep -Eq '^[a-z][a-z0-9-]*[a-z0-9]$'; then
  echo "error: target name must be kebab-case" >&2
  exit 2
fi

REPO="$HOME/Projects/agents"
VSRC="$REPO/hermes/profiles/$SRC"
VDST="$REPO/hermes/profiles/$DST"
RSRC="$HOME/.hermes/profiles/$SRC"
RDST="$HOME/.hermes/profiles/$DST"

[ -d "$VSRC" ] || { echo "error: versioned source missing: $VSRC" >&2; exit 3; }
[ -d "$RSRC" ] || { echo "error: runtime source missing: $RSRC"   >&2; exit 4; }

# 1. Versioned copy (idempotent)
if [ -d "$VDST" ]; then
  echo "skip versioned: $VDST already exists"
else
  echo "copy versioned: $VSRC → $VDST"
  cp -R "$VSRC" "$VDST"
fi

# 2. Runtime copy (idempotent)
if [ -d "$RDST" ]; then
  echo "skip runtime:   $RDST already exists"
else
  echo "copy runtime:   $RSRC → $RDST"
  cp -R "$RSRC" "$RDST"
fi

# 3. Rewrite identifying fields so validate-profile.sh passes:
#    - manifest.json `.sku`         → target name
#    - a2a-card.json `.agent_id`    → target name
patch_field () {
  local file="$1" field="$2" target="$3"
  [ -f "$file" ] || return 0
  local current
  current=$(python3 -c "import json; print(json.load(open('$file')).get('$field',''))")
  if [ "$current" = "$target" ]; then
    echo "skip patch:     $file already $field=$target"
    return 0
  fi
  echo "patch:          $file ($field: $current → $target)"
  python3 - "$file" "$field" "$target" <<'PY'
import json, sys
path, field, target = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as f:
    data = json.load(f)
data[field] = target
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
}

for D in "$VDST" "$RDST"; do
  patch_field "$D/manifest.json" sku       "$DST"
  patch_field "$D/a2a-card.json" agent_id  "$DST"
done

# 4. Validate the versioned target
echo "validate:       running scripts/validate-profile.sh $DST"
"$REPO/scripts/validate-profile.sh" "$DST"

# 5. Print deferred manual steps
cat <<EOF

--- deferred (run when ready) ---
LiteLLM key alias mint (run from a shell with LITELLM_MASTER_KEY exported):
  curl -X POST http://127.0.0.1:4000/key/generate \\
    -H "Authorization: Bearer \$LITELLM_MASTER_KEY" \\
    -H "Content-Type: application/json" \\
    -d '{"key_alias":"$DST-key","duration":null}'

Langfuse project tag (from Langfuse UI at http://localhost:3200, or via API
with LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY):
  curl -X POST http://localhost:3200/api/public/projects \\
    -u "\$LANGFUSE_PUBLIC_KEY:\$LANGFUSE_SECRET_KEY" \\
    -H "Content-Type: application/json" \\
    -d '{"name":"$DST"}'
EOF

echo "done: shadow workspace $DST ready."
