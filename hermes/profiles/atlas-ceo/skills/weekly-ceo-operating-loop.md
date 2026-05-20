# weekly-ceo-operating-loop

Use when Atlas prepares a recurring weekly owner/operator cadence for Alex.

## Loop

1. Get a fresh source packet.
2. Triage freshness, confidence, missing signals, and contradictions.
3. Produce the CEO brief.
4. Name one proposal-worthy decision, if any.
5. If Alex asks, create a proposed-only PFOS action row.

## Promotion rule

Atlas can move from manual brief to scheduled watcher only after:

- a source-grounded brief passes evals,
- the premium model route is healthy or degraded output is clearly labeled,
- the live Slack brief changes Alex's weekly decision,
- proposal writes land as `proposed` and never execute.

## Event emission (after follow-up lands)

After recording a follow-up brief (Step 4 or 5), emit a safe
`atlas.follow_up.recorded` event per
`_meta/decisions/2026-05-18-hermes-pfos-event-contract.md` via:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile atlas-ceo \
  --tool atlas.record_follow_up \
  --extra-json '{"follow_up_ref":"<id>","decision_outcome":"<approved|rejected|deferred>","source_packet_ref":"<id-or-summary>"}'
```

No raw packet text, no decision body in the event — only classification + refs.
