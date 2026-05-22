# MEMORY — morning-logs

## Boot anchors

- PFOS workbench path is frozen.
- Hermes WebUI is the operating surface.
- Fleet summarizes operations.
- Labyrinth explains runs and failures.
- Morning Logs v0.1 is read-only/propose-only.
- Business collectors come later.

## First-loop questions

1. Is Hermes usable right now?
2. What is broken?
3. Which profile/event/approval needs Alex next?
4. Where should Alex inspect first?

## Current first workflow

Morning Logs reads Hermes dashboard/runtime state, writes one local report, and emits one redacted event. It never executes the recommended action.
