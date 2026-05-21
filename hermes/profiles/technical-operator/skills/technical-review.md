---
name: technical-review
description: Procedural engineering review of one target artifact (skill file, build script, ADR, .planning/ plan, or PR diff). Returns one critique with verdict, findings, inversion, and approval gate.
input: required `target:` path or PR ref. Optional `scope:` (full/diff/risk), optional `compare:` for diff context.
output: markdown to ~/Projects/agents/_inbox/technical-operator-reviews/{YYYY-MM-DD}-review-{slug}.md plus paired PFOS event
---

# Skill: technical-review

## Purpose

Read one target artifact and return a procedural engineering review with a verdict. The critique is the only output; the technical-operator profile never modifies the target.

This skill is the only profile-local skill in `technical-operator` at rung 1. It is invoked manually (no cron) via `bash scripts/fleet-invoke.sh technical-operator technical-review 'target: <path>'` or equivalent Hermes call.

## Inputs (must read before producing a critique)

1. `SOUL.md`, `DOCTRINE.md`, `USER.md`, `MEMORY.md` (profile context).
2. **The target artifact at the path provided** — read it fully. If the target is a directory, refuse and ask for a specific file path.
3. **Cross-referenced files**:
   - For a skill file: the profile's `config.yaml` (verify event contract conformance), `CLAUDE.md` (verify event type appears), related ADRs the skill cites.
   - For a build script: callers (`grep -rn '<script-name>' ~/Projects/agents/`), validator scripts (e.g., `lint-profile.sh`, `validate-agency-skills.py`), output paths.
   - For an ADR: every entry in `related_adrs:` and `supersedes:`.
   - For a `.planning/` plan: every file the plan declares it will modify, plus any referenced prior plans.
   - For a PR diff: full `git diff base..head`, touched files at HEAD, the PR description.
4. **Doctrine canon**:
   - `~/.claude/references/compound-engineering-policy.md` (DRY/KISS/YAGNI/SOLID/SINE)
   - `_meta/decisions/2026-05-18-agent-shape-11-file-contract.md`
   - `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`
   - `_meta/decisions/2026-05-20-reserve-codex-for-tool-use-technical-operator-profile.md`

If any required input is missing or unreadable, halt and return a structured `blocked` output naming the missing input. Do not invent context.

## Procedure

1. **Restate the target** in one sentence: what the artifact does and why it was changed.
2. **Identify the door classification**: TYPE-1 (one-way, hard to reverse) or TYPE-2 (two-way, revertible). If unclear, default to TYPE-1 and explain the ambiguity in the inversion section.
3. **Apply the doctrine canon to the artifact**:
   - Surgical-change test: do all changes trace to the stated intent?
   - DRY/KISS/YAGNI/SOLID/SINE checks: any violations?
   - Hidden authority creep: new tool? new channel? new MCP write? new write_scope outside the profile?
   - Event contract conformance: every emit-tool has a complete `event:` block with matching `CLAUDE.md` reference?
   - Eval coverage: any new code path without a fixture?
   - Margin of safety on TYPE-1 changes: kill-switch + rollback + monitoring signal all present?
4. **Run the inversion**: assume this shipped 90 days ago and broke catastrophically. What probably caused it?
5. **Assign verdict** by counting findings and weighing severity:
   - Any `BLOCK` finding → verdict `BLOCK`.
   - One or more `SHIP-RISK-MEDIUM` findings → verdict `SHIP-RISK-MEDIUM` (unless every finding has a documented fix shape and reversibility is TYPE-2, in which case `SHIP-RISK-LOW` is acceptable).
   - No findings or only `SHIP-RISK-LOW` findings → verdict `SHIP-RISK-LOW`.
6. **Name the approval gate**: what specific evidence (file change, test added, ADR written, kill-switch wired) would flip the verdict to `SHIP-RISK-LOW`?
7. **Write the critique** to `~/Projects/agents/_inbox/technical-operator-reviews/{YYYY-MM-DD}-review-{slug}.md` using the output contract below.
8. **Emit the PFOS event** via the canonical emitter (see § Emit safe event summary).

## Decision rules

- If the artifact has zero risk signal and no doctrine violations, the verdict is `SHIP-RISK-LOW` and the critique says so plainly. **Do not manufacture findings.** A clean review is an acceptable output.
- If the artifact contains TYPE-1 risk (credentials, schema, external send, irreversible mutation) without a named rollback + kill-switch + monitoring signal, the verdict is `BLOCK` and at least one finding is `BLOCK` severity.
- If you cannot read a required cross-referenced file, the critique is `blocked` (not `BLOCK` — a different state) and lists the missing inputs.
- If the target is outside the profile's read scope (e.g., a private credentials file, a `memory-vault-private/` path), refuse and return a `scope-denied` output.
- Findings never include patched code. They name the fix shape only ("extract this into a helper," "add an early return for empty input," "add an eval fixture for the new decision path").

## Output destination

Write Markdown to:

`~/Projects/agents/_inbox/technical-operator-reviews/{YYYY-MM-DD}-review-{slug}.md`

The `{slug}` is derived from the target path (last meaningful component, kebab-case). Example: target `hermes/profiles/marin/skills/aeo-opportunity-scout.md` → slug `marin-aeo-opportunity-scout`.

Do not render an HTML companion unless the critique is being promoted to an operator artifact (a separate decision, not part of the default skill output).

## Output contract

```markdown
---
date: <YYYY-MM-DD>
type: technical-review
target: <path or PR ref>
verdict: <BLOCK | SHIP-RISK-MEDIUM | SHIP-RISK-LOW>
door_classification: <TYPE-1 | TYPE-2>
findings_count:
  block: <N>
  medium: <N>
  low: <N>
pfos_event_id: <UUID filled after emit, or "pending" if dry-run>
---

# Technical Review: <one-line summary of target>

## Summary

<≤3 sentences: what the change does, what could go wrong, what the verdict turns on.>

## Verdict: <BLOCK | SHIP-RISK-MEDIUM | SHIP-RISK-LOW>

Door: <TYPE-1 | TYPE-2>. <One sentence justifying the door classification.>

## Findings

### F1 — <short title> [<BLOCK | SHIP-RISK-MEDIUM | SHIP-RISK-LOW>]

- **Evidence:** `<file:line>` or `<evidence path>`
- **Risk:** <what could go wrong, plain English>
- **Fix shape:** <what kind of change would address this; not the patched code>

### F2 — ...

(Repeat for each finding. If no findings, write `_None._`)

## Inversion

Assume this shipped 90 days ago and broke catastrophically. The probable cause: <one sentence>.

## Approval gate

To flip this verdict to `SHIP-RISK-LOW`, the following specific evidence must hold:

- <bullet 1>
- <bullet 2>
- ...

If verdict is already `SHIP-RISK-LOW`, this section reads: `_No flip needed; verdict is already SHIP-RISK-LOW._`
```

## Constraints

- Use this as a procedural skill workflow, not as a persona or autonomous agent.
- Do not create new Hermes profiles, dispatch subagents, or claim persistent memory beyond `MEMORY.md`.
- Do not modify the review target. Read-only.
- Do not write outside `~/Projects/agents/_inbox/technical-operator-reviews/`.
- Do not send anything externally — no Slack, email, GitHub comments, PR review submissions, Sentry tickets.
- Do not include patched code in findings.
- Do not reference the artifact author. Critique the artifact.
- State missing inputs (return `blocked` output) instead of inventing context.

## Emit safe event summary

After the critique file is written, run the canonical emitter so PFOS records the inbox entry:

```bash
source ~/.config/prettyfly-marketing/hermes-tokens.env
test -f ~/Projects/agents/scripts/emit-agent-event.py || {
  echo "blocked: emitter script missing at ~/Projects/agents/scripts/emit-agent-event.py" >&2
  exit 1
}
python3 ~/Projects/agents/scripts/emit-agent-event.py \
  --profile technical-operator \
  --tool technical_review.propose \
  --readout-path "_inbox/technical-operator-reviews/<YYYY-MM-DD>-review-<slug>.md" \
  --decision "<BLOCK | SHIP-RISK-MEDIUM | SHIP-RISK-LOW>" \
  --extra-json '{"target_path":"<target>","door_classification":"<TYPE-1|TYPE-2>","findings_count_block":<N>,"findings_count_medium":<N>,"findings_count_low":<N>}'
```

The emitter derives `agent_slug=technical-operator` from `config.profile`. The event lands with `type=technical_operator.review.proposed`, `cwd_project=agents`, `skill_slug=technical-review`. Capture the row UUID printed to stdout and patch the critique file's frontmatter `pfos_event_id:` field before considering the invocation complete.

## Validation

- Every finding cites a `file:line` or evidence path. No source = no finding.
- The verdict is one of the three allowed values; no "it depends."
- The inversion section names a specific probable cause; not "I don't know."
- The approval gate is concrete (specific files, specific tests, specific ADRs); not "more review."
- The PFOS row exists in `public.agent_events` (verify via SQL).
- The frontmatter `pfos_event_id:` matches the UUID printed by the emitter.
