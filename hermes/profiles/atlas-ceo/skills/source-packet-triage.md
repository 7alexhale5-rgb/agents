# source-packet-triage

Use before Atlas makes a CEO recommendation from `fleet.snapshot` or any other
source packet.

## Job

Decide whether the packet is strong enough for a source-grounded recommendation.

## Checks

1. Identify packet timestamp, source names, freshness, confidence, and
   `missing_signals`.
2. Separate verified facts from assumptions.
3. Flag stale, absent, or contradictory signals.
4. Inspect `decision_feedback_recent` for approved/rejected patterns and the
   reason Alex gave.
5. If the packet is insufficient, say exactly what is missing and recommend the
   smallest next signal to collect.
6. If the packet is sufficient, proceed to the relevant Atlas skill and cite
   source signals by name.

## Output

- `source status`: sufficient, partial, or insufficient
- `verified signals`: short list
- `missing signals`: short list
- `recent decision feedback`: sparse, useful, or contradictory
- `recommendation permission`: proceed, proceed with caveats, or do not brief

Never invent a missing metric to make the brief feel complete.
