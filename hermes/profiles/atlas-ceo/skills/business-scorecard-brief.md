# business-scorecard-brief

Use when Alex asks what the business needs, what the scorecard says, or what
Atlas would prioritize from PFOS signals.

## Required input

A verified packet from `business.scorecard.snapshot` or `fleet.snapshot`.

## Output

1. `Scorecard status`: sufficient, partial, or insufficient
2. `Current constraint`
3. `Diagnosis`
4. `Top priorities`: one to three
5. `Non-priority`
6. `Decision Alex must make`
7. `Risk I am watching`
8. `Source signals`
9. `Missing signals`

## Rules

- Business scorecard means business and fleet signals first: silos, proposal
  pipeline, pending actions, costs, evals, and runtime health.
- Do not pull in calendar, inbox, or personal-life recommendations unless the
  packet already contains aggregate signals and Alex asks for them.
- Prefer one bottleneck over a broad status tour.
