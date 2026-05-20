#!/usr/bin/env bash
# lint-profile.sh - soft-lint Hermes profiles against the Atlas-shaped contract.

set -euo pipefail

ROOT_DIR="${AGENTS_ROOT:-$HOME/Projects/agents}"
PROFILES_DIR="${HERMES_PROFILES_DIR:-$ROOT_DIR/hermes/profiles}"
MODE="${LINT_PROFILE_MODE:-soft}" # soft exits 0 on warnings; hard exits 1.

REQUIRED_FILES=(
  SOUL.md
  DOCTRINE.md
  USER.md
  MEMORY.md
  CLAUDE.md
  manifest.json
  a2a-card.json
  config.yaml
  PAUSED.template
  changelog.md
)
REQUIRED_DIRS=(skills eval)

warn() {
  printf 'WARN %s: %s\n' "$1" "$2"
}

check_json() {
  local file="$1"
  python3 - "$file" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    json.load(fh)
PY
}

check_yaml() {
  local file="$1"
  python3 - "$file" <<'PY'
import sys

try:
    import yaml  # type: ignore
except Exception:
    raise SystemExit(0)

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    yaml.safe_load(fh)
PY
}

lint_one() {
  local name="$1"
  local dir="$PROFILES_DIR/$name"
  local warnings=0

  if [[ ! -d "$dir" ]]; then
    warn "$name" "profile directory missing: $dir"
    return 1
  fi

  for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$dir/$file" ]]; then
      warn "$name" "missing file: $file"
      warnings=$((warnings + 1))
    fi
  done

  for subdir in "${REQUIRED_DIRS[@]}"; do
    if [[ ! -d "$dir/$subdir" ]]; then
      warn "$name" "missing directory: $subdir"
      warnings=$((warnings + 1))
    fi
  done

  if [[ ! -L "$dir/AGENTS.md" ]]; then
    warn "$name" "AGENTS.md must be a symlink to CLAUDE.md"
    warnings=$((warnings + 1))
  elif [[ "$(readlink "$dir/AGENTS.md")" != "CLAUDE.md" ]]; then
    warn "$name" "AGENTS.md symlink target must be CLAUDE.md"
    warnings=$((warnings + 1))
  fi

  if [[ -f "$dir/manifest.json" ]] && ! check_json "$dir/manifest.json"; then
    warn "$name" "manifest.json is not valid JSON"
    warnings=$((warnings + 1))
  fi

  if [[ -f "$dir/a2a-card.json" ]] && ! check_json "$dir/a2a-card.json"; then
    warn "$name" "a2a-card.json is not valid JSON"
    warnings=$((warnings + 1))
  fi

  if [[ -f "$dir/config.yaml" ]] && ! check_yaml "$dir/config.yaml"; then
    warn "$name" "config.yaml is not valid YAML"
    warnings=$((warnings + 1))
  fi

  # Event-contract cross-check: every event.type declared in config.yaml must
  # appear in CLAUDE.md (per _meta/decisions/2026-05-18-hermes-pfos-event-contract.md).
  if [[ -f "$dir/config.yaml" && -f "$dir/CLAUDE.md" ]]; then
    while IFS= read -r event_type; do
      [[ -z "$event_type" ]] && continue
      if ! grep -qF "$event_type" "$dir/CLAUDE.md"; then
        warn "$name" "event type declared in config.yaml not documented in CLAUDE.md: $event_type"
        warnings=$((warnings + 1))
      fi
    done < <(python3 - "$dir/config.yaml" <<'PY'
import sys
try:
    import yaml
except ImportError:
    sys.exit(0)
with open(sys.argv[1]) as fh:
    cfg = yaml.safe_load(fh) or {}
contracts = (cfg.get("tools") or {}).get("contracts") or {}
for tool_cfg in contracts.values():
    if not isinstance(tool_cfg, dict):
        continue
    event = tool_cfg.get("event") or {}
    etype = event.get("type")
    if etype:
        print(etype)
PY
    )
  fi

  if [[ -d "$dir/skills" ]]; then
    while IFS= read -r entry; do
      if [[ -d "$entry" ]]; then
        warn "$name" "nested skill directory not allowed: ${entry#$dir/}"
        warnings=$((warnings + 1))
      elif [[ "$(basename "$entry")" == ".gitkeep" ]]; then
        continue
      elif [[ "$entry" != *.md ]]; then
        warn "$name" "skills must be Markdown files: ${entry#$dir/}"
        warnings=$((warnings + 1))
      fi
    done < <(find "$dir/skills" -mindepth 1 -maxdepth 1 -print | sort)
  fi

  if [[ "$warnings" -eq 0 ]]; then
    printf 'PASS %s\n' "$name"
  else
    printf 'SOFT-WARN %s: %s warning(s)\n' "$name" "$warnings"
  fi

  [[ "$warnings" -eq 0 ]]
}

targets=()
if [[ "${1:-}" == "--all" || -z "${1:-}" ]]; then
  while IFS= read -r dir; do
    targets+=("$(basename "$dir")")
  done < <(find "$PROFILES_DIR" -mindepth 1 -maxdepth 1 -type d -print | sort)
else
  targets=("$@")
fi

total=0
passed=0
warned=0

for profile in "${targets[@]}"; do
  total=$((total + 1))
  if lint_one "$profile"; then
    passed=$((passed + 1))
  else
    warned=$((warned + 1))
  fi
done

printf -- '----\n'
printf 'Profiles checked: %s; passed: %s; warned: %s; mode: %s\n' "$total" "$passed" "$warned" "$MODE"

if [[ "$MODE" == "hard" && "$warned" -gt 0 ]]; then
  exit 1
fi

exit 0
