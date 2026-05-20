# approval-proposal-draft

Use when Alex wants Atlas to turn a recommendation into an approval-ready PFOS
proposal.

## Required fields

- `recommended_action`
- `door_type`: one-way or two-way
- `approval_gate`
- `expected_upside`
- `downside_risk`
- `stop_doing`
- `confidence`
- `source_packet_id` or `source_summary`

## Rules

- Create proposals only with `atlas.propose_action`.
- A proposal is not execution.
- Never say the action was approved, sent, dispatched, deployed, or completed.
- Inspect `decision_feedback_recent` before proposing. Do not repeat a rejected
  pattern unless you can name what changed.
- If recent feedback is sparse, say that plainly instead of pretending Atlas has
  learned a preference.
- If the source packet is stale or missing, draft the proposal text but do not
  write the PFOS row.

## Event emission (after proposal lands)

After writing the PFOS proposal row, emit a safe `atlas.action.proposed` event
per `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md` via:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile atlas-ceo \
  --tool atlas.propose_action \
  --extra-json '{"door_type":"<one-way|two-way>","confidence":"<low|med|high>","approval_gate":"<short>","source_packet_ref":"<id-or-summary>"}'
```

Capture the returned row UUID into the proposal record's footer as
`pfos_event_uuid: <uuid>`. Confirm exit 0. Event must not include
`recommended_action` body, `source_packet` raw text, or any secret — only
classification fields per the ADR.
