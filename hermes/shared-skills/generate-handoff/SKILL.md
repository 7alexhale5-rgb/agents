---
name: generate-handoff
description: Produce a canonical cross-session handoff for Hermes profile work.
---

# Skill: generate-handoff

Use this when a Hermes profile or build session needs to transfer work to a later session without losing context.

## Inputs

- Project or profile name
- Current phase and ship gate
- What is done
- What remains
- Validation commands
- Critical references
- Hard constraints
- Intended next-session entry point

## Procedure

1. Read the current profile `CLAUDE.md`, latest relevant plan, and latest handoff if one exists.
2. Capture only durable state: files created, decisions made, validation results, blockers, and next actions.
3. Keep secrets, raw private messages, memory dumps, and long transcripts out of the handoff.
4. Write the handoff as Markdown with YAML frontmatter.
5. Include a pasteable resume prompt in a fenced code block.

## Output Shape

Use this structure:

- YAML frontmatter: date, type, project, tags, status, parent_plan, session_predecessor
- `# Handoff: <title>`
- `## State At Handoff`
- `## What Remains`
- `## Validation Steps`
- `## Critical References`
- `## Hard Constraints`
- `## Resume Prompt`

The resume prompt must be a fenced `text` block that can be pasted directly into a fresh Claude Code or Codex session.

## Quality Bar

- The next agent should not need to ask where files live.
- The handoff should name the next smallest useful action.
- The handoff should preserve boundaries, not expand scope.
- If a gate is not passed, say exactly what is missing.
