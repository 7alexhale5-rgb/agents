# approval-proposal-draft

Use when Alex wants Atlas to turn a recommendation into an approval-ready Hermes
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
  write the Hermes local receipt.

## Receipt (after proposal lands)

After writing the Hermes local proposal receipt, verify it records `type=atlas.action.proposed`, the profile, tool, source packet reference, door type, confidence, and approval gate. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.

Capture the receipt ID in the proposal record footer as `receipt_id: <uuid>`. The receipt must not include `recommended_action` body, raw `source_packet` text, or any secret.
