---
name: self-audit
description: Run Atlas's own eval suite + sample recent CEO briefs, write evidence, emit atlas.action.proposed event (audit_type=self). Catches advisor drift. Scheduled Sundays 6am.
input: none
output: markdown to hermes/profiles/atlas-ceo/eval/{YYYY-MM-DD}-self-audit.md + paired atlas.action.proposed Hermes event (audit_type=self)
---

# Skill: self-audit

## Purpose

Weekly self-grading. Atlas's eval suite at
`hermes/profiles/atlas-ceo/eval/promptfoo.yaml` currently points at an
archived `pf-runtime/scripts/eval_profile_prompt.py` path. Atlas's
self-audit works around this by using promptfoo's `anthropic:messages`
provider directly (same pattern Quill + Stet use). Eventually the eval
suite gets fixed — a separate Atlas patch tracked in the migration
runbook.

## Procedure

1. Run the eval suite with the anthropic provider override:
   ```bash
   cd /Users/alexhale/Projects/agents/hermes/profiles/atlas-ceo
   # Atlas's current promptfoo.yaml is broken (archived exec path).
   # If the suite fails to invoke, write evidence with the failure
   # and continue — the eval-path fix is a separate patch.
   npx promptfoo eval -c eval/promptfoo.yaml --no-cache --output /tmp/atlas-eval-$(date +%Y%m%d).json || echo '{"results":{"stats":{"successes":0,"failures":0}},"failed":true}' > /tmp/atlas-eval-$(date +%Y%m%d).json
   ```
2. Sample the last 7 days of CEO briefs from Atlas's workspace +
   `cron/output/` if scheduled briefs landed there. Capture: brief
   filename, age, decision named, source signals cited, whether a
   matching Hermes local receipt exists.
3. Write evidence to
   `hermes/profiles/atlas-ceo/eval/{YYYY-MM-DD}-self-audit.md` with
   frontmatter matching the fleet self-audit shape, plus
   `eval_blocked_by:` if the eval invocation itself failed (so the gate
   watcher sees the blocker explicitly).
4. Write the receipt:
   ```text
Write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
```

## Anti-patterns

- Inventing eval results when the underlying suite is broken — flag the
  blocker, emit the event, surface to Alex.
- Same as the other profiles' self-audits — no skipping, no editing
  failing tests, always list failures.

## Failure modes

- The eval suite is currently structurally broken (archived path). v1
  self-audit reports this honestly and emits anyway so the gate watcher
  has a row. Fix-path: separate Atlas patch to port eval invocation to
  the anthropic:messages provider, same as Quill/Stet.
