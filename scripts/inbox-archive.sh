#!/usr/bin/env bash
# inbox-archive.sh — age out marketing-vault inbox files older than 14 days.
#
# Files in:
#   ~/Projects/marketing/_inbox/cmo-readouts/
#   ~/Projects/marketing/_inbox/quill-drafts/
#   ~/Projects/marketing/_inbox/stet-critiques/
# that are older than 14 days move to ~/Projects/marketing/_inbox/_archive/YYYY-WW/.
#
# Files mentioned in any agent_events row with status='approved' get flagged
# (printed to stderr) for Alex to promote manually — not archived.
#
# Run daily via launchd: com.prettyfly.marketing-inbox-archive

set -euo pipefail

INBOX_ROOT="$HOME/Projects/marketing/_inbox"
ARCHIVE_ROOT="$INBOX_ROOT/_archive"
AGE_DAYS=14

mkdir -p "$ARCHIVE_ROOT"

archived=0
flagged=0
skipped=0

for dir in cmo-readouts quill-drafts stet-critiques; do
  src="$INBOX_ROOT/$dir"
  [[ -d "$src" ]] || continue

  while IFS= read -r -d '' f; do
    base="$(basename "$f")"
    [[ "$base" == ".gitkeep" ]] && continue

    # Use mod-time as the "age" proxy. Filenames embed dates but mtime is the
    # honest signal for "still being touched".
    week="$(date -r "$f" '+%Y-W%V')"
    target="$ARCHIVE_ROOT/$week/$dir"

    # If a recent agent_events row references this file with status='approved',
    # flag for Alex to promote manually instead of archiving. We do this via a
    # tiny supabase probe — if it returns >0 rows, we flag.
    rel="_inbox/$dir/$base"
    cnt="$(cd "$HOME/Projects/prettyfly-os" && echo "SELECT count(*) FROM public.agent_events WHERE status='approved' AND data->>'readout_path'='$rel';" 2>/dev/null | supabase db query --linked 2>/dev/null | grep -o '"count": [0-9]*' | grep -o '[0-9]*' || echo "0")"

    if [[ "$cnt" -gt 0 ]]; then
      echo "FLAG: $rel — approved but still in inbox (promote manually)" >&2
      flagged=$((flagged+1))
      continue
    fi

    mkdir -p "$target"
    mv "$f" "$target/"
    archived=$((archived+1))
  done < <(find "$src" -maxdepth 1 -type f -mtime "+$AGE_DAYS" -print0)
done

echo "inbox-archive: archived=$archived flagged=$flagged skipped=$skipped"
