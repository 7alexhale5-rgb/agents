---
name: self-audit
description: Run CMO's own promptfoo eval suite, write evidence to eval/, emit cmo.eval.completed event. Catches profile drift without manual eval runs. Scheduled Sundays 6am.
input: none
output: markdown to hermes/profiles/cmo/eval/{YYYY-MM-DD}-self-audit.md + paired cmo.eval.completed PFOS event
---

# Skill: self-audit

## Purpose

Weekly self-grading. CMO runs its own eval suite + samples its own recent
outputs, writes evidence, emits a `cmo.eval.completed` event with pass rate.
The fleet's autonomy-gate watcher reads these events to decide when CMO can
graduate to auto-approve.

## Procedure

1. Run the eval suite:
   ```bash
   cd /Users/alexhale/Projects/agents/hermes/profiles/cmo
   npx promptfoo eval -c eval/promptfoo.yaml --no-cache --output /tmp/cmo-eval-$(date +%Y%m%d).json
   ```
2. Parse the JSON output. Compute `pass_rate = passed / total`, list failed
   test descriptions, capture token cost.
3. Sample the last 7 days of readouts from
   `~/Projects/marketing/_inbox/cmo-readouts/` — list filenames, ages, and
   whether each has a matching `agent_events` row.
4. Write evidence to
   `hermes/profiles/cmo/eval/{YYYY-MM-DD}-self-audit.md` with frontmatter:
   ```yaml
   ---
   date: { YYYY-MM-DD }
   type: self-audit
   profile: cmo
   eval_id: { promptfoo eval ID }
   pass_rate: { 0.0-1.0 }
   tests_run: { N }
   tests_failed: [{ test description }, ...]
   recent_readouts: [{ filename, age_days, has_event_row }, ...]
   token_cost_usd: { N.NN }
   ---
   ```
5. Emit the event:
   ```bash
   python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
     --profile cmo \
     --tool weekly_decision.propose \
     --readout-path "hermes/profiles/cmo/eval/<YYYY-MM-DD>-self-audit.md" \
     --extra-json '{"audit_type":"self","pass_rate":<N>,"tests_run":<N>,"tests_failed":<N>}'
   ```
   (Reusing the existing `weekly_decision.propose` tool because it carries
   the correct `cmo.weekly_decision.proposed` event type; the `audit_type`
   field in data distinguishes self-audits from production readouts. Future
   refactor: add a dedicated `cmo.eval.completed` event type if the volume
   warrants.)

## Anti-patterns

- Skipping the eval run because "nothing changed this week" — that's drift's
  exact disguise
- Editing failed tests to make them pass (eval test quality matters more
  than the pass rate itself)
- Reporting pass_rate without listing which tests failed

## Failure modes

- promptfoo command fails (ANTHROPIC_API_KEY missing) → write evidence file
  with `eval_id: failed`, `pass_rate: null`, `failure_reason: <reason>`, emit
  event anyway so the gate watcher knows the audit ran (and failed)
- promptfoo runs but all tests timeout → same: evidence + event with failure
  reason
