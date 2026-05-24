---
name: coding-session-review
description: Read-only review of a coding session's request, repo state, diff, validation evidence, and next 1% move. Produces one session receipt; never edits source.
input: required `session:` summary or handoff path. Optional `repo:` path, optional `scope:` (current/diff/full), optional `evidence:` paths to test logs, screenshots, PRs, or operator artifacts.
output: markdown to ~/Projects/agents/_inbox/technical-operator-reviews/{YYYY-MM-DD}-session-{slug}.md plus Hermes local receipt
---

# Skill: coding-session-review

## Purpose

Review one coding session as an operating artifact. The output is a session receipt that tells Alex what changed, what is proven, what remains risky, what should be captured, and the next 1% developer move.

This is not a coding skill. It never modifies source files, commits, pushes, deploys, reruns CI, edits environment variables, or sends external messages.

## Inputs

Read only what exists. If a required input is missing, return `blocked` and name the missing input.

1. `SOUL.md`, `DOCTRINE.md`, `USER.md`, `MEMORY.md`.
2. The `session:` input:
   - a user request;
   - a handoff path;
   - a PR/ref;
   - or a short session summary.
3. Repo state for `repo:` or the current working tree:
   - `git status --short`;
   - `git diff --stat`;
   - `git diff` for touched source and docs;
   - recent commits touching the target files when relevant.
4. Validation evidence when present:
   - test, build, lint, typecheck, or smoke output;
   - screenshots or rendered operator artifacts;
   - generated inbox artifacts.
5. Relevant project memory only when needed:
   - latest handoff/session note;
   - relevant ADR;
   - existing technical-operator review for the same surface.

Do not read private credentials, token files, raw private vault payloads, or unrelated repos just to make the review feel complete.

## Procedure

1. **Classify the session** as one of: feature, bugfix, integration, UI, data/security, ops/runtime, refactor, planning/docs.
2. **Restate the intent** in one sentence using the user request or handoff.
3. **Inventory the change surface**:
   - files changed;
   - generated artifacts;
   - runtime/profile/config surfaces touched;
   - any external services implicated.
4. **Check validation evidence**:
   - what ran;
   - what did not run;
   - whether the visible/user-facing artifact was checked.
5. **Apply technical-operator doctrine**:
   - surgical-change test;
   - DRY/KISS/YAGNI/SOLID/SINE;
   - Karpathy gate: smallest slice + falsifiable proof;
   - VanClief boundary: one owner, visible context, no authority blur;
   - Will workflow fit: repeated workflow, existing tools first, no agent bloat;
   - compound value: makes the next session cheaper, safer, or clearer;
   - hidden authority creep;
   - event/approval boundaries;
   - missing eval or receipt evidence.
6. **Assign a verdict**:
   - `BLOCK` when the session changed risky surfaces without evidence or crosses authority boundaries.
   - `SHIP-RISK-MEDIUM` when the work is plausible but validation, scope, or memory capture is incomplete.
   - `SHIP-RISK-LOW` when the change is bounded, evidence is present, and the next step is clear.
7. **Name the memory capture**:
   - no capture needed;
   - update handoff/session note;
   - add ADR;
   - update operator artifact;
   - run a follow-up technical review.
8. **Name the compound capture**: what lesson, artifact, or validation result
   should make the next session easier.
9. **Name the next 1% developer move** as one concrete action that can be done
   next without re-planning. Include expected payoff and why it beats broader work.
10. **Name promotion evidence**: whether this receipt counts toward the
    10-receipt / 2-week proof window.
11. **Write the session receipt** to `_inbox/technical-operator-reviews/`.
12. **Write the Hermes local receipt** using `technical_review.propose` with `skill_slug=technical-review` until a separate write tool is approved by ADR.

## Output destination

Write Markdown to:

`~/Projects/agents/_inbox/technical-operator-reviews/{YYYY-MM-DD}-session-{slug}.md`

The `{slug}` comes from the repo, feature, or handoff name. Keep it short.

## Output contract

```markdown
---
date: <YYYY-MM-DD>
type: coding-session-review
target: <repo path, handoff path, PR ref, or summary slug>
session_class: <feature | bugfix | integration | ui | data-security | ops-runtime | refactor | planning-docs>
verdict: <BLOCK | SHIP-RISK-MEDIUM | SHIP-RISK-LOW>
receipt_id: <UUID filled after emit, or "pending" if dry-run>
---

# Coding Session Review: <one-line session name>

## Summary

<3 sentences max: intent, change surface, verdict.>

## What Changed

- <changed surface 1>
- <changed surface 2>

## Validation Evidence

- <command/artifact/evidence path> — <pass/fail/not-run/unknown>

## Findings

### F1 — <short title> [<BLOCK | SHIP-RISK-MEDIUM | SHIP-RISK-LOW>]

- **Evidence:** `<file:line>` or `<artifact path>`
- **Failure type:** <correctness risk | authority creep | context rot | missing validation | non-compounding work>
- **Risk:** <plain-English risk>
- **Fix shape:** <shape only; no patch>

(If no findings, write `_None._`)

## Engineering Principle Scorecard

| Principle | Result | Evidence |
| --- | --- | --- |
| SINE | <pass | watch | fail> | <file/artifact/evidence> |
| SOLID | <pass | watch | fail> | <file/artifact/evidence> |
| DRY | <pass | watch | fail> | <file/artifact/evidence> |
| KISS | <pass | watch | fail> | <file/artifact/evidence> |
| YAGNI | <pass | watch | fail> | <file/artifact/evidence> |
| Compound | <pass | watch | fail> | <file/artifact/evidence> |
| Karpathy gate | <pass | watch | fail> | <file/artifact/evidence> |
| VanClief boundary | <pass | watch | fail> | <file/artifact/evidence> |
| Will workflow fit | <pass | watch | fail> | <file/artifact/evidence> |

## Memory Capture

<none | update handoff/session note | add ADR | update operator artifact | run follow-up review>

## Compound Capture

<lesson, artifact, or validation result that should make the next session cheaper, safer, or clearer>

## 1% Engineering Move

- **Action:** <one concrete next action>
- **Expected payoff:** <why this improves the system>
- **Why this beats broader work:** <one sentence>

## Promotion Evidence

<counts toward 10 receipts / does not count; include why>
```

## Constraints

- Use this as a procedural workflow, not a persona.
- Do not create profiles, subagents, cron jobs, tools, channels, or new event types.
- Do not modify source files or the review target.
- Do not write outside `_inbox/technical-operator-reviews/`.
- Do not include patched code in findings.
- Do not claim validation ran unless evidence exists.
- Do not promote the workflow until at least 10 real receipts across at least 2 weeks show it improves continuity.
- Keep the skill concise. Add no reference files unless this file approaches 500 lines or repeated use proves a stable reference is needed.

## Validation

- The receipt names the session class.
- The receipt distinguishes proven evidence from missing evidence.
- Every finding cites a file line or artifact path.
- The scorecard has all nine principle rows.
- The 1% engineering move is a single concrete action with payoff and tradeoff.
- The compound capture says how the next session gets cheaper, safer, or clearer.
- Promotion evidence says whether the receipt counts toward the proof window.
- The output stays within technical-operator's rung-1 authority.
