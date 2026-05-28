# weekly-ceo-operating-loop

Use when Atlas prepares a recurring weekly owner/operator cadence for Alex.

## Ralph loop entry

Before working any step, **set a `/goal`** so the operating loop iterates under
the judge instead of completing in a single turn. The judge re-evaluates after
each turn; if the brief is incomplete or fabricated metrics slip in, the loop
continues. Turn budget is the backstop.

```text
/goal Produce one source-grounded weekly CEO brief for Alex, naming ≤3
priorities with cited source signals, classifying any proposal-worthy
decision (one-way/two-way door risk + named approval gate), and emitting
one atlas.follow_up.recorded event with data.goal_iteration populated.
Treat the goal as done only when (a) the brief is delivered, (b) every
priority traces to a source signal in fleet.snapshot or
business.scorecard.snapshot, and (c) the follow-up event lands. Treat the
goal as blocked (and stop) if no source packet is available, the premium
Anthropic route is degraded, or fabricated metrics are detected on
self-audit.
```

Default turn budget (20) is sufficient. Override with `/goal --max-turns N`
only when explicitly extending under a stop-sign condition.

## Pre-pitch step — absorb operator rejections

Before fetching the source packet, run the shared `review-rejections` skill (at `hermes/shared-skills/review-rejections/SKILL.md`). It prints a Markdown block titled "Rejected pitches still worth absorbing" listing every cockpit-operator rejection of an Atlas-authored pitch from the last 30 days, with verbatim reasons.

Treat the block as prior-art constraint for this session: if the brief you're about to draft would repeat a recently rejected idea, either name the rejection and explain how this version addresses it, or pick a different priority. If the block says "None in the last 30 days," continue normally.

Executable form: `HERMES_PROFILE_NAME=atlas-ceo bash hermes/shared-skills/review-rejections/rehearsal.sh --read-only`.

## Loop

1. Get a fresh source packet (`fleet.snapshot` or `business.scorecard.snapshot`).
2. Triage freshness, confidence, missing signals, and contradictions.
3. Produce the CEO brief — ≤3 priorities, each cited to a source signal.
4. Name one proposal-worthy decision, if any (one-way/two-way door + approval gate).
5. If Alex asks, create a proposed-only Hermes action row.

## Promotion rule

Atlas can move from manual brief to scheduled watcher only after:

- a source-grounded brief passes evals,
- the premium model route is healthy or degraded output is clearly labeled,
- the live Slack brief changes Alex's weekly decision,
- proposal writes land as `proposed` and never execute.

## Receipt (after follow-up lands)

After recording a follow-up brief (Step 4 or 5), verify a Hermes local receipt records `type=atlas.follow_up.recorded`, `follow_up_ref`, `decision_outcome`, `source_packet_ref`, and `goal_iteration` so the Ralph loop remains auditable. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.

`<N>` is the current iteration of the active `/goal` — `1` on the first pass,
incremented when the judge sends the agent back for another turn. The judge
verdict is fail-open per Hermes goals.py; trust the turn budget as backstop.

No raw packet text, no decision body in the event — only classification + refs.

## Closing the goal

After the brief is delivered AND the event lands, the agent should explicitly
state "goal complete: weekly brief delivered, event <uuid> emitted" so the
auxiliary judge concludes `done`. If a stop-sign fires (no source packet,
degraded premium route, fabricated metrics on self-audit), state the block
clearly so the judge concludes `done` with reason and the loop halts cleanly.
