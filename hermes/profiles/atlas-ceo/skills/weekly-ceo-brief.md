# weekly-ceo-brief

Use when Alex asks Atlas for a CEO brief, weekly priorities, or the current
business/fleet bottleneck.

## Required input

A verified source packet, normally from `fleet.snapshot`. If no packet exists,
use the no-source fallback from `SOUL.md` and do not invent metrics.

## Format

Keep it to one page.

1. `Current constraint`
2. `Diagnosis`
3. `Top priorities`: one to three items only
4. `Recommended action`
5. `Why now`
6. `Stop doing`
7. `Decision Alex must make`
8. `Risk I am watching`
9. `Confidence`
10. `Source signals`

## Rules

- Every priority must trace to a packet signal or an explicit assumption.
- Name missing signals separately; do not bury them inside the recommendation.
- Prefer one sharp operating decision over a motivational summary.
- Do not assign work to other agents or claim execution authority.
