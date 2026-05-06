#!/usr/bin/env bash
# Hermes commit-watcher — Phase 4.7 pre-work item C.
# Daily 02:30 ET via launchd. Diffs ~/.hermes/hermes-agent HEAD..origin/main and
# emails the result to forge-audit (operator scans for security-relevant fixes).
#
# Per ADR-006 §3: Hermes is pinned at v0.12.0. We do NOT pull. We just watch.
# Operator decides whether to port a security fix manually.

set -euo pipefail

HERMES_REPO="$HOME/.hermes/hermes-agent"
LOG_DIR="$HOME/Assets/logs"
LOG_FILE="$LOG_DIR/hermes-commit-watcher.log"
DIGEST_DIR="$HOME/Projects/agents/_meta/runbooks/hermes-commit-digests"
TODAY=$(date +%Y-%m-%d)
DIGEST_FILE="$DIGEST_DIR/$TODAY.md"

mkdir -p "$LOG_DIR"

# Refuse to write into a symlinked digest dir — defends against an attacker
# (or a stray symlink) redirecting digests outside the intended runbook tree.
if [ -L "$DIGEST_DIR" ]; then
    echo "[$(date +%Y-%m-%d)] hermes-commit-watcher: $DIGEST_DIR is a symlink, refusing to write" >> "$LOG_FILE"
    exit 1
fi
mkdir -p "$DIGEST_DIR"

if [ ! -d "$HERMES_REPO/.git" ]; then
    echo "[$TODAY] hermes-commit-watcher: $HERMES_REPO is not a git repo, skipping" >> "$LOG_FILE"
    exit 0
fi

cd "$HERMES_REPO"

# Fetch quietly (do NOT merge or pull)
if ! git fetch --quiet origin 2>>"$LOG_FILE"; then
    echo "[$TODAY] hermes-commit-watcher: fetch failed" >> "$LOG_FILE"
    exit 0
fi

PINNED_REF=$(git rev-parse HEAD)
UPSTREAM_REF=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master 2>/dev/null || echo "")

if [ -z "$UPSTREAM_REF" ]; then
    echo "[$TODAY] hermes-commit-watcher: could not resolve upstream ref" >> "$LOG_FILE"
    exit 0
fi

COMMITS_BEHIND=$(git rev-list --count "$PINNED_REF..$UPSTREAM_REF" 2>/dev/null || echo "?")

cat > "$DIGEST_FILE" <<EOF
# Hermes commit digest — $TODAY

- **Pinned at:** \`$PINNED_REF\` (v0.12.0 per ADR-006)
- **Upstream HEAD:** \`$UPSTREAM_REF\`
- **Commits behind:** $COMMITS_BEHIND

## Recent upstream commits (last 50)

\`\`\`
$(git log --oneline "$PINNED_REF..$UPSTREAM_REF" 2>/dev/null | head -50 || echo "(no commits or git error)")
\`\`\`

## Security-relevant scan

Searching commit messages for: security, CVE, fix, vulnerability, auth, token, leak

\`\`\`
$(git log --oneline --grep='security\|CVE\|vulnerability\|auth bypass\|token leak\|RCE\|XSS\|injection' "$PINNED_REF..$UPSTREAM_REF" 2>/dev/null | head -20 || echo "(none found)")
\`\`\`

## Action

- Operator reviews this digest in the next \`forge-audit\` session.
- If a security-relevant commit is identified, port manually (cherry-pick or read + reimplement). Do **not** run \`hermes update\`.
- If no action: archive this digest in place; next watcher run overwrites tomorrow's.
EOF

echo "[$TODAY] hermes-commit-watcher: $COMMITS_BEHIND commits behind, digest at $DIGEST_FILE" >> "$LOG_FILE"
