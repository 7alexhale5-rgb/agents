#!/usr/bin/env bash
# pair-telegram.sh — pair a Telegram bot to a Hermes profile
#
# Usage: pair-telegram.sh <profile-name> <bot-token>
#
# Notes:
#   - Get the bot token from @BotFather on Telegram (/newbot)
#   - This script writes to BOTH the versioned profile .env AND the runtime ~/.hermes/profiles/<name>/.env
#   - Token is masked in any echo; only the last 4 chars print
#   - For mike-lawdbot rotation procedure, use this AFTER /revoke + new token from BotFather

set -euo pipefail

NAME="${1:-}"
TOKEN="${2:-}"

if [ -z "$NAME" ] || [ -z "$TOKEN" ]; then
  echo "usage: pair-telegram.sh <profile-name> <bot-token>" >&2
  echo "       (get token from @BotFather; this script never echoes the full token)" >&2
  exit 1
fi

# Validate token shape (Telegram tokens are <num>:<35-char-base64>)
if ! echo "$TOKEN" | grep -Eq '^[0-9]+:[A-Za-z0-9_-]{30,}$'; then
  echo "error: bot token doesn't look like a Telegram token (expected <num>:<35-char-base64>)" >&2
  exit 2
fi

SRC=$HOME/Projects/agents/hermes/profiles/$NAME
RT=$HOME/.hermes/profiles/$NAME

if [ ! -d "$SRC" ]; then
  echo "error: versioned profile not found: $SRC" >&2
  exit 3
fi

# The env-var name follows the convention TELEGRAM_BOT_TOKEN_<PROFILE_UPPER>
ENV_VAR_NAME="TELEGRAM_BOT_TOKEN_$(echo "$NAME" | tr '[:lower:]-' '[:upper:]_')"

# Update the versioned tree's .env (creates if missing; never commits — .env is gitignored)
SRC_ENV="$SRC/.env"
if [ -f "$SRC_ENV" ] && grep -q "^${ENV_VAR_NAME}=" "$SRC_ENV"; then
  # Replace existing line (BSD sed compatible)
  sed -i.bak "s|^${ENV_VAR_NAME}=.*|${ENV_VAR_NAME}=${TOKEN}|" "$SRC_ENV"
  rm "${SRC_ENV}.bak"
else
  echo "${ENV_VAR_NAME}=${TOKEN}" >> "$SRC_ENV"
fi
chmod 600 "$SRC_ENV"
echo "  versioned: $SRC_ENV  (token …${TOKEN: -4})"

# Update the runtime .env
if [ -d "$RT" ]; then
  RT_ENV="$RT/.env"
  if [ -f "$RT_ENV" ] && grep -q "^${ENV_VAR_NAME}=" "$RT_ENV"; then
    sed -i.bak "s|^${ENV_VAR_NAME}=.*|${ENV_VAR_NAME}=${TOKEN}|" "$RT_ENV"
    rm "${RT_ENV}.bak"
  else
    echo "${ENV_VAR_NAME}=${TOKEN}" >> "$RT_ENV"
  fi
  chmod 600 "$RT_ENV"
  echo "  runtime:   $RT_ENV  (token …${TOKEN: -4})"
else
  echo "  runtime:   not yet created — run 'hermes profile create $NAME' then re-run this script"
fi

# Probe the bot to confirm token is live
BOT_INFO=$(curl -fsS "https://api.telegram.org/bot${TOKEN}/getMe" 2>/dev/null || true)
if echo "$BOT_INFO" | grep -q '"ok":true'; then
  USERNAME=$(echo "$BOT_INFO" | grep -oE '"username":"[^"]+"' | cut -d'"' -f4)
  echo
  echo "✓ token verified — paired to bot @${USERNAME}"
  echo
  echo "next:"
  echo "  1. Update $SRC/config.yaml — set channels.telegram.enabled: true"
  echo "  2. Run: scripts/sync-profile.sh push $NAME"
  echo "  3. Restart: hermes profile restart $NAME"
  echo "  4. Open Telegram, send /start to @${USERNAME}, confirm reply"
else
  echo
  echo "⚠ token write succeeded, but Telegram getMe failed — verify token is correct" >&2
  exit 4
fi
