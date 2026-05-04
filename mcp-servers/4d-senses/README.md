# 4d-senses MCP server

Wraps the existing 4D-senses hook stack (`~/.claude/hooks/sense-*.js`, `~/.claude/scripts/4d-auto-vision.py`, `~/.claude/scripts/watch-video.py`) as a stdio MCP server so any Hermes profile can consult the senses as tools.

## Why

Alex's hooks fire automatically inside Claude Code (PostToolUse / UserPromptSubmit). Hermes profiles need access to the same signal stream — smell warnings, pain history, intuition pattern matches, vision reports — but they aren't running inside the Claude Code event loop. This MCP server is the bridge.

Hook events also keep flowing into the senses' shared state (logs, intuition database, vision report directory). The MCP just reads from that shared state.

## Tools exposed

| Tool                           | Purpose                                                                   |
| ------------------------------ | ------------------------------------------------------------------------- |
| `senses_smell_recent`          | Recent code-smell warnings (god files, deep nesting, dup, secrets, TODOs) |
| `senses_pain_active`           | Active pain incidents — repeated failure patterns + auto-checkpoints      |
| `senses_intuition_for_pattern` | Match a piece of text or a planned action against past feedback memory    |
| `senses_vision_latest`         | Latest 4D-auto-vision report (URL → frames + gemini_perception.md)        |
| `senses_status`                | One-page summary of what's firing, recent counts, alert level             |

## Install in a Hermes profile

In `~/.hermes/profiles/<name>/config.yaml`:

```yaml
mcp_servers:
  4d-senses:
    command: node
    args: ["~/Projects/agents/mcp-servers/4d-senses/index.js"]
    include:
      [smell_recent, pain_active, intuition_for_pattern, vision_latest, status]
```

Then in any skill that wants the awareness, prefix tool calls with `mcp_4d-senses_*`.

## Why MCP and not a direct hook

Hermes is a separate process from Claude Code. Hooks are Claude Code's eventing system. MCP is the universal tool protocol both speak. Wrapping the senses behind MCP means the same agent can read them whether it's running inside Claude Code, Cursor, Codex, or Hermes — single source of truth, multiple consumers.

## Smoke test

```bash
node smoke.js
```

Expected output: tool list with 5 entries, sample call to `senses_status` returns a summary string.
