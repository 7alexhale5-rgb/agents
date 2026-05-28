---
name: review-rejections
description: Read recent operator rejections of this profile's prior pitches and surface them in the working context before pitching new work.
---

# Skill: review-rejections

Use this at the start of any wake cycle where the profile may pitch new tasks.

**Phase A (current): read-only.** The skill surfaces operator feedback so the agent's LLM can absorb it. It writes nothing. Decision branching and re-pitch authority are deferred to Phase B; do not invent them here.

## Why this exists

Today, when the cockpit operator rejects a triage task, Hermes archives the task and records `task_comments(author='operator-cockpit', body='Rejected by operator: <reason>')`. Nothing wakes the agent that pitched it. This skill closes that gap by making the agent read its own rejection feedback before composing the next pitch — the operator's "no, because X" enters the agent's working context as prior-art constraint.

## Inputs

- `$HERMES_PROFILE_NAME` — required. Identifies the profile whose rejections to surface. If unset, log to stderr and exit 0 (no-op).
- No other inputs. The skill is invoked with no arguments.

## Procedure

1. **Guard on identity.** If `$HERMES_PROFILE_NAME` is empty or unset, write `[review-rejections] skipped: no $HERMES_PROFILE_NAME` to stderr and stop. Do not crash.

2. **Pull recent archived tasks.** Run:
   ```bash
   hermes kanban list --status archived --archived --json
   ```
   Output is a JSON array of task records. Each record carries `id`, `title`, `created_by`, `created_at`, plus other fields the skill ignores.

3. **Filter to this profile's recent rejections.** Keep only records where:
   - `created_by == $HERMES_PROFILE_NAME` — the profile authored this pitch
   - `created_at >= now_seconds - (30 * 86400)` — within the last 30 days

   The recency window caps the surface to actionable feedback. Older rejections are archaeology.

4. **For each surviving task, fetch comments.** Run:
   ```bash
   hermes kanban show <task.id> --json
   ```
   Parse `.comments` — an array of `{author, body, created_at}`. Pull every comment where `author == "operator-cockpit"` (this is the cockpit's signature on its Reject calls; pinned by `lib/hermes/kanban.ts:rejectKanbanTask` in the prettyfly-os repo).

5. **Compose the working-context block.** Emit a Markdown block to stdout, titled and formatted exactly so the calling LLM can absorb it as prior-art:

   ```
   ## Rejected pitches still worth absorbing

   The cockpit operator rejected these prior pitches. Read the reasons before composing new pitches in this session. If a new pitch would repeat a recently rejected idea, either name the rejection and explain how this version addresses it, or pick a different priority.

   - **<title>** (`<id>`, rejected <YYYY-MM-DD>)
     Reason: "<verbatim operator comment body>"

   - **<title>** (`<id>`, rejected <YYYY-MM-DD>)
     Reason: "<verbatim operator comment body>"
   ```

   Order: most recent rejection first (sort by the operator-cockpit comment's `created_at` descending). If a task has multiple operator-cockpit comments (the operator re-rejected after a re-pitch — Phase B territory), use the most recent one only.

6. **Empty case.** If no rejections survive filtering, emit:
   ```
   ## Rejected pitches still worth absorbing

   None in the last 30 days.
   ```
   Still emit the heading so the calling skill sees a consistent shape.

## Failure handling

- `hermes kanban list` returns non-zero: log `[review-rejections] hermes kanban list failed (exit N); skipping rejection review` to stderr and exit 0. Don't block the wake cycle on Hermes being down.
- A `hermes kanban show` call fails for a single task: log the task id + error to stderr, skip that task, continue with the rest.
- JSON parse error: same — log + skip + continue.

## Boundaries (Phase A)

- The skill writes nothing. No new tasks. No new comments. No state files.
- The skill makes no decisions. It surfaces the operator's feedback verbatim and lets the calling LLM reason about it.
- The skill does not deduplicate by "already processed." Every wake re-surfaces the same recent rejections until they fall out of the 30-day window. This is intentional in Phase A: persistent reminders, no marker complexity. Phase B will add the comment-as-marker pattern + a single-flight lock once we know whether that's worth the moving parts.

## Output contract

- Single Markdown block on stdout, starting with `## Rejected pitches still worth absorbing`.
- Exit 0 on success, on empty, on no-profile, and on Hermes-down. Exit 0 is "the wake cycle should continue normally" — there's never an actionable failure here.
- Any logging goes to stderr.

## Verification

The companion `rehearsal.sh` in this directory is the verify gate. Run:

```bash
HERMES_PROFILE_NAME=atlas-ceo bash hermes/shared-skills/review-rejections/rehearsal.sh
```

It seeds a triage task as `atlas-ceo`, rejects it via the cockpit BFF, runs this skill's procedure, prints the result, and cleans up. The expected output names the seeded title and the verbatim reason. See the script for the cleanup contract.
