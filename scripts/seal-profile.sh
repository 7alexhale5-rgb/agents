#!/usr/bin/env bash
# seal-profile.sh — kill-switch a profile by writing the PAUSED file
#
# Usage:
#   seal-profile.sh <profile-name>            # write PAUSED to runtime + versioned
#   seal-profile.sh <profile-name> --release  # remove PAUSED (resume runtime)

set -euo pipefail

NAME="${1:-}"
ACTION="${2:-pause}"

if [ -z "$NAME" ]; then
  echo "usage: seal-profile.sh <profile-name> [--release]" >&2
  exit 1
fi

SRC="$HOME/Projects/agents/hermes/profiles/$NAME"
RT="$HOME/.hermes/profiles/$NAME"

case "$ACTION" in
  pause|"")
    echo "sealing $NAME (writing PAUSED file)"
    [ -d "$SRC" ] && touch "$SRC/PAUSED" && echo "  versioned: $SRC/PAUSED"
    [ -d "$RT" ]  && touch "$RT/PAUSED"  && echo "  runtime:   $RT/PAUSED"
    echo "done. profile is halted. release with: seal-profile.sh $NAME --release"
    ;;
  --release|release)
    echo "releasing $NAME (removing PAUSED file)"
    [ -f "$SRC/PAUSED" ] && rm "$SRC/PAUSED" && echo "  removed: $SRC/PAUSED"
    [ -f "$RT/PAUSED" ]  && rm "$RT/PAUSED"  && echo "  removed: $RT/PAUSED"
    echo "done."
    ;;
  *)
    echo "unknown action: $ACTION" >&2
    exit 2
    ;;
esac
