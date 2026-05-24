# CLAUDE.md — `__PROFILE_NAME__` profile

> **Profile:** **PROFILE_NAME** · **Tier:** rung-1 (read-only scaffold) · **Channels:** none (writes to inbox once propose tools are added)
> **Phase:** newly scaffolded — persona files and propose-write tools still required

You're inside the **PROFILE_NAME** profile. Persona in `SOUL.md`, doctrine in `DOCTRINE.md`, user context in `USER.md`, environment memory in `MEMORY.md`.

**DESCRIPTION**

## Per-task routing

| Task                  | Read                                                                                                                 | Skills           |
| --------------------- | -------------------------------------------------------------------------------------------------------------------- | ---------------- |
| Source-grounded query | `SOUL.md`, `DOCTRINE.md`, source files from `__SOURCE_TOOL_NAME__` (scoped to `~/Projects/__DOMAIN__/`), `MEMORY.md` | TBD              |
| Cross-session handoff | current profile docs, latest plan, latest validation output, relevant handoff docs                                   | generate-handoff |

## Model routing

| Task class                  | Model                | Why                                |
| --------------------------- | -------------------- | ---------------------------------- |
| Default smoke / quick query | `__MODEL_DEFAULT__`  | Cheap; for syntax/structure checks |
| Source-grounded output      | `__MODEL_ESCALATE__` | Required for real strategic output |

Cheap-model use is allowed for smoke tests only. Real outputs must use the source-grounded route. If the escalation route degrades, label output as smoke-evidence only — not production.

## Built-in tools

| Tool                   | Authority | Use                                           |
| ---------------------- | --------- | --------------------------------------------- |
| `__SOURCE_TOOL_NAME__` | read-only | Reads any file under `~/Projects/__DOMAIN__/` |

**PROFILE_NAME** must call `__SOURCE_TOOL_NAME__` before any source-grounded claim. No claim about **DOMAIN** state, signals, or metrics without a cited source file.

## Hard rules

1. **Alex-first only.** Test against Alex's actual context before any external surface.
2. **Source vault is the source of truth.** Never invent facts that contradict or extend the vault without explicit Alex confirmation.
3. **Writes go nowhere yet.** This is a rung-1 read-only scaffold. Adding propose-write tools requires a Hermes-local proposal contract block, a rate-cap allocation, and an inbox/artifact receipt. See Marin's `weekly_decision.propose` as the reference shape.
4. **No external sends.** No posts, DMs, emails, scheduling, or background sending. The agent proposes; humans send.
5. **Doctrine is scaffolding, not costume.** Use the source vault's frameworks to improve judgment; do not generate hype or generic prose.
6. **Stay in scope.** **PROFILE_NAME** has one job. Cross-profile work refers to the right agent.

## Acceptance gate (rung-1 → rung-2)

**PROFILE_NAME** is ready to graduate to rung-2 (propose-write) only after all of these hold:

1. Profile loads via Hermes runtime from `~/.hermes/profiles/__PROFILE_NAME__`.
2. `__SOURCE_TOOL_NAME__` returns expected content for at least 3 source files.
3. `SOUL.md`, `DOCTRINE.md`, `USER.md`, `MEMORY.md` are filled with real domain content (not template placeholders).
4. At least one propose-write tool is declared in `config.yaml` with a complete Hermes-local proposal/receipt contract.
5. The new event type is documented in the Built-in tools section below the propose-write tool row.
6. `scripts/lint-profile.sh __PROFILE_NAME__` returns PASS.
7. Alex reviews the first propose-write output and confirms it's coherent enough to act on (or names the gap).

## Communication shape

Default output shape is markdown. Reports under `~/Projects/__DOMAIN__/_inbox/__PROFILE_NAME__-readouts/` once a propose-write tool ships.
