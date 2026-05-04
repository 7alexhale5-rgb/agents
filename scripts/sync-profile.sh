#!/usr/bin/env bash
# sync-profile.sh — keep versioned source-of-truth in sync with Hermes runtime
#
# Usage:
#   sync-profile.sh pull <profile-name>     # runtime → versioned (after agent learned new skill)
#   sync-profile.sh push <profile-name>     # versioned → runtime (after git pull brought updates)
#   sync-profile.sh status <profile-name>   # show diff between versioned and runtime
#
# Versioned source-of-truth: ~/Projects/agents/hermes/profiles/<name>/
# Runtime:                   ~/.hermes/profiles/<name>/

set -euo pipefail

DIR="${1:-}"; NAME="${2:-}"

if [ -z "$DIR" ] || [ -z "$NAME" ]; then
  echo "usage: sync-profile.sh <pull|push|status> <profile-name>" >&2
  exit 1
fi

SRC="$HOME/Projects/agents/hermes/profiles/$NAME"
RT="$HOME/.hermes/profiles/$NAME"

if [ ! -d "$SRC" ]; then
  echo "error: versioned profile dir not found: $SRC" >&2
  exit 2
fi

# Files we sync (versioned → runtime AND runtime → versioned)
TRACKED=(
  "CLAUDE.md" "SOUL.md" "USER.md" "MEMORY.md" "AGENTS.md"
  "manifest.json" "pricing.yaml" "config.yaml"
  ".env.example" "PAUSED.template" "changelog.md"
)

# Directories we sync (recursive)
TRACKED_DIRS=(
  "rooms" "skills" "eval"
)

# Files we NEVER sync (runtime-only)
EXCLUDED=(
  ".env" "memory/state.db" "memory/trajectories" "scratch" "workspace"
)

case "$DIR" in
  pull)
    if [ ! -d "$RT" ]; then
      echo "error: runtime profile dir not found: $RT  (run hermes profile create $NAME first)" >&2
      exit 3
    fi
    echo "pulling $NAME runtime → versioned"
    for f in "${TRACKED[@]}"; do
      if [ -f "$RT/$f" ]; then
        cp -p "$RT/$f" "$SRC/$f"
        echo "  $f"
      fi
    done
    for d in "${TRACKED_DIRS[@]}"; do
      if [ -d "$RT/$d" ]; then
        rsync -a --delete "$RT/$d/" "$SRC/$d/"
        echo "  $d/"
      fi
    done
    echo "done. review with: git -C $HOME/Projects/agents diff hermes/profiles/$NAME"
    ;;
  push)
    if [ ! -d "$RT" ]; then
      echo "creating runtime dir: $RT"
      mkdir -p "$RT"
    fi
    echo "pushing $NAME versioned → runtime"
    for f in "${TRACKED[@]}"; do
      if [ -f "$SRC/$f" ]; then
        cp -p "$SRC/$f" "$RT/$f"
        echo "  $f"
      fi
    done
    for d in "${TRACKED_DIRS[@]}"; do
      if [ -d "$SRC/$d" ]; then
        rsync -a --delete "$SRC/$d/" "$RT/$d/"
        echo "  $d/"
      fi
    done
    echo "done."
    ;;
  status)
    if [ ! -d "$RT" ]; then
      echo "$NAME: no runtime dir (yet)"
      exit 0
    fi
    echo "diff $NAME (versioned vs runtime):"
    for f in "${TRACKED[@]}"; do
      if [ -f "$SRC/$f" ] && [ -f "$RT/$f" ]; then
        if ! diff -q "$SRC/$f" "$RT/$f" >/dev/null 2>&1; then
          echo "  modified: $f"
        fi
      elif [ -f "$SRC/$f" ]; then
        echo "  versioned-only: $f"
      elif [ -f "$RT/$f" ]; then
        echo "  runtime-only: $f"
      fi
    done
    ;;
  *)
    echo "usage: sync-profile.sh <pull|push|status> <profile-name>" >&2
    exit 1
    ;;
esac
