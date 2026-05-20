---
name: self-audit
description: Run Quill's own promptfoo eval suite, write evidence to eval/, emit quill.eval.completed event. Catches profile drift without manual eval runs. Scheduled Sundays 6am.
input: none
output: markdown to hermes/profiles/quill/eval/{YYYY-MM-DD}-self-audit.md + paired quill.draft.proposed PFOS event (audit_type=self)
---

# Skill: self-audit

## Purpose

Weekly self-grading. Quill runs its own eval suite + samples its own recent
drafts, writes evidence, emits a paired event with pass rate. The fleet's
autonomy-gate watcher reads these to decide when Quill can graduate to
auto-emission for the campaign-authorized next move.

## Procedure

1. Run the eval suite:
   ```bash
   cd /Users/alexhale/Projects/agents/hermes/profiles/quill
   npx promptfoo eval -c eval/promptfoo.yaml --no-cache --output /tmp/quill-eval-$(date +%Y%m%d).json
   ```
2. Parse the JSON output. Compute `pass_rate`, list failed test descriptions,
   capture token cost.
3. Sample the last 7 days of drafts from
   `~/Projects/marketing/_inbox/quill-drafts/` — list filename, age,
   pillar, sweeps_passed status, content_rule_links completeness, whether
   each has a matching `agent_events` row.
4. Write evidence to
   `hermes/profiles/quill/eval/{YYYY-MM-DD}-self-audit.md` with frontmatter
   matching the Marin self-audit shape, plus `recent_drafts:` array of the
   draft summary list.
5. Emit the event:
   ```bash
   python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
     --profile quill \
     --tool draft_field_note.propose \
     --readout-path "hermes/profiles/quill/eval/<YYYY-MM-DD>-self-audit.md" \
     --extra-json '{"audit_type":"self","pass_rate":<N>,"tests_run":<N>,"tests_failed":<N>}'
   ```
   (Reuses `draft_field_note.propose` for now; same rationale as Marin's
   self-audit. `audit_type=self` in data distinguishes from production
   drafts.)

## Anti-patterns

- Same as Marin self-audit: skipping eval because nothing visibly changed;
  editing failing tests; reporting pass_rate without listing failures.

## Failure modes

- Same handling as Marin: eval failure still emits an event with `failure_reason`
  set so the gate watcher knows the audit ran.
