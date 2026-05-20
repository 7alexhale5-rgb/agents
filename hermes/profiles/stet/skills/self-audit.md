---
name: self-audit
description: Run Stet's own promptfoo eval suite, write evidence to eval/, emit stet.critique.proposed event (audit_type=self). Catches critic drift without manual eval runs. Scheduled Sundays 6am.
input: none
output: markdown to hermes/profiles/stet/eval/{YYYY-MM-DD}-self-audit.md + paired stet.critique.proposed PFOS event (audit_type=self)
---

# Skill: self-audit

## Purpose

Weekly self-grading. Stet runs its own eval suite + samples its own recent
critiques, writes evidence, emits a paired event with pass rate + a verdict
distribution. The fleet's autonomy-gate watcher reads these to decide when
Stet can graduate to auto-routing critiques on inbox-land without Alex
gating each one.

## Procedure

1. Run the eval suite:
   ```bash
   cd /Users/alexhale/Projects/agents/hermes/profiles/stet
   npx promptfoo eval -c eval/promptfoo.yaml --no-cache --output /tmp/stet-eval-$(date +%Y%m%d).json
   ```
2. Parse output: `pass_rate`, failed tests, token cost.
3. Sample the last 7 days of critiques from
   `~/Projects/marketing/_inbox/stet-critiques/` — list filename, verdict
   (SHIP/REVISE/KILL), kill_triggers_hit count, target_artifact_path,
   matching `agent_events` row presence.
4. Compute verdict distribution: `{ship: N, revise: N, kill: N}`.
5. Write evidence to
   `hermes/profiles/stet/eval/{YYYY-MM-DD}-self-audit.md` with frontmatter
   matching Marin/Quill shape, plus `recent_critiques:` array and
   `verdict_distribution:` object.
6. Emit the event:
   ```bash
   python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
     --profile stet \
     --tool critique_draft.propose \
     --readout-path "hermes/profiles/stet/eval/<YYYY-MM-DD>-self-audit.md" \
     --extra-json '{"audit_type":"self","pass_rate":<N>,"tests_run":<N>,"tests_failed":<N>,"verdict_distribution":{"ship":<N>,"revise":<N>,"kill":<N>}}'
   ```

## Anti-patterns

- Same as Marin/Quill — no skipping, no editing failing tests to inflate pass
  rate, always list failures.
- Specific to Stet: do NOT self-critique critique quality (that's a meta-loop
  Viper would love but adds zero value — eval suite already checks for
  source-citation + verdict presence + fix-path).

## Failure modes

- Same as Marin/Quill.
