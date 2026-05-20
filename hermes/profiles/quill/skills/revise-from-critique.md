---
name: revise-from-critique
description: Read a Viper critique from _inbox/viper-critiques/ and produce a revised draft addressing each finding. Output is a new draft file, not an edit-in-place.
input: critique file path under _inbox/viper-critiques/ + original draft file path
output: revised markdown to ~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-{type}-{slug}-r{N}.md + paired quill.draft.proposed PFOS event
---

# Skill: revise-from-critique

## Purpose

Read a Viper critique, produce a NEW draft file that addresses each finding without losing the original's intent. Never edit the original draft in-place — Alex compares the two.

## Inputs

1. `SOUL.md`, `DOCTRINE.md`, `MEMORY.md`
2. Target critique at `~/Projects/marketing/_inbox/viper-critiques/<file>.md` (full read)
3. Original draft at `~/Projects/marketing/_inbox/quill-drafts/<file>.md` (full read)
4. `~/Projects/marketing/brand/copy-review-checklist.md`
5. `~/Projects/marketing/brand/voice-and-anti-slop.md`
6. The original draft's source files (per the original's frontmatter `content_rule_links`)

## Procedure

1. **Parse the critique.** Viper critiques follow this shape:
   - Per-sweep findings (Clarity / Voice / So-what / Proof / Specificity / CTA / Compliance)
   - Each finding: severity (critical / warn / info), specific line/phrase quoted, named fix or hard-block
   - Overall verdict: `SHIP` / `REVISE` / `KILL`

   If the verdict is `KILL`, surface to Alex without revising — kills require Alex decision, not auto-revision.
   If the verdict is `SHIP`, surface to Alex without revising — no work needed.
   Only proceed with revision when the verdict is `REVISE`.

2. **Confirm the critique applies to the named original draft.** Check the critique frontmatter `target_draft_path` matches the original draft path. If mismatch, hold + surface.

3. **For each finding, apply the named fix or hard-block:**
   - `critical` severity findings: MUST be addressed in the revision, or the revision is itself a `KILL` candidate (surface why if you can't address it)
   - `warn` severity findings: SHOULD be addressed; if not addressed, frontmatter must explain why
   - `info` severity findings: address if it doesn't conflict with intent; otherwise leave with a note

4. **Re-apply the 7 sweeps** to the revised draft. The revision must pass all sweeps that the original failed, AND must not introduce new failures in sweeps the original passed.

5. **Content Rule check**: revision must preserve or improve the 5-link completeness.

6. **Banned vocab sweep**: same as the originating draft skill.

7. **Write** to `~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-{original-type}-{original-slug}-r{N}.md` where `{N}` is the revision number (r2 for the first revision, r3 for second, etc.). Frontmatter MUST include:
   - `type: quill-draft`
   - `status: proposed`
   - All original `content_rule_links`
   - `revision_of: <original draft path>`
   - `addresses_critique: <critique path>`
   - `findings_addressed: <list of finding IDs from the critique>`
   - `findings_not_addressed: <list + reason for each, if any>`

8. **Emit PFOS event**:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile quill \
  --tool draft_revision.propose \
  --readout-path "_inbox/quill-drafts/<YYYY-MM-DD>-<original-type>-<original-slug>-r<N>.md" \
  --extra-json '{"revision_of":"<original path>","addresses_critique":"<critique path>","findings_addressed_count":<N>,"verdict_after":"<self-assessment>"}'
```

## Anti-patterns

- Editing the original draft in-place — always produce a new file
- Auto-revising a critique with verdict `SHIP` (no work needed) or `KILL` (Alex decides)
- Addressing critical findings with cosmetic changes that don't actually resolve the finding
- Introducing new banned vocab while fixing sweep failures
- Cutting a sentence that was the draft's spine just to satisfy a length warning
- Losing the Content Rule links during revision

## Failure modes

- Critique verdict is `SHIP` → surface "no revision needed" and exit
- Critique verdict is `KILL` → surface "Alex decision required" and exit
- Critique target_draft_path mismatch → hold + surface
- Cannot address a `critical` finding without breaking the draft → produce a revision that flags `findings_not_addressed: [{id, reason}]` and recommends Alex re-scope or kill
- Re-running the 7 sweeps on the revision produces NEW failures → produce r{N+1} addressing both old + new before declaring done
