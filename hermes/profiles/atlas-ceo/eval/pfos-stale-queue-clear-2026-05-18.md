# PFOS Stale Queue Clear Evidence - 2026-05-18

Status: production mutation completed; no provider execution.

## Source

- Input artifact: `pfos-approval-queue-triage-2026-05-18`
- Original source packet: `atlas-atlas-ceo-1779080714434`
- Post-clear source packet: `atlas-atlas-ceo-1779081874252`
- Adopted decision: `clear_pending_approval_queue_before_new_surface_area`

## Mutation Summary

- Target rows: 20 packet-visible `agent_actions`
- Final action status: 20 `rejected`
- Provider executions: 0
- Rows with `executed_at` set: 0
- Paired rejection events: 20
- Decision surface: `pfos_stale_queue_clear`
- Event payload privacy: `private_payload_redacted=true`

Grouped reasons:

| Reason | Count | Applies to |
| --- | ---: | --- |
| `stale_external_side_effect_regenerate_if_needed` | 9 | `inbox.unsubscribe_draft` |
| `stale_time_sensitive_context_regenerate_if_needed` | 11 | `calendar.hold`, `inbox.follow_up_task`, `inbox.reply_draft` |

## Verification

- All 20 target ids now have `status=rejected`.
- All 20 target ids still have `executed_at=null`.
- Exactly 20 `agent.action.rejected` events were recorded for the target ids.
- Every rejection event has `execution_triggered=false`.
- Every rejection event has `private_payload_redacted=true`.
- Every rejection event uses the expected grouped stale-context reason.
- Re-fetched Atlas source packet no longer includes any of the 20 target ids in
  `pending_agent_actions`.

The post-clear source packet still reports 20 pending actions from the wider
PFOS backlog. Those are outside this packet-20 lane and should be handled by a
fresh triage pass if Atlas keeps seeing a congested approval loop.

## Evidence Event Ids

- `94b9da15-2992-4958-b6dc-e6cef079c872`
- `21afb592-29c4-479e-9fc9-46a4e176090a`
- `e23f29d1-5861-4ff0-9b30-95f2e8647d0e`
- `3c3460fe-a631-443e-ab27-4a023bc3b6b5`
- `f285b427-fdc2-4ef2-9bc1-83463e8dc504`
- `4fcf5a24-cf79-46e3-a52d-cd4a738a9263`
- `dfe1dda6-c86a-4a78-8702-6d2655921d21`
- `4a583ec5-652a-484e-89f7-8174dddc5fc5`
- `f8d85063-7e8d-4117-8869-1376a8ee8e4d`
- `b67756cf-cd1e-4045-a7e1-0b7e89e128f4`
- `82cd8263-492d-4c53-910c-3a1068be4554`
- `03083ae2-8107-461b-8600-f06ea5c5aa24`
- `4a1030ad-c9f0-4cdf-b89d-b10a4993cb44`
- `c7326afc-b8bb-4ab7-bdf1-713352dbece3`
- `79a087da-25bf-47dc-bc50-83d1d59944fb`
- `3e8da43e-4d37-493b-a87f-8bd6e72213c0`
- `00c07bb1-d9d8-415a-bdfe-105037681b54`
- `c417d677-b6fd-427e-b712-434fece17546`
- `cee3b24c-fc84-413d-a017-7f4a5760c790`
- `01d020a8-f28e-4c5f-a6a7-8eaf2304cfe6`

## Next Regeneration Rule

Atlas should treat stale queue entries as regeneration triggers, not approval
candidates. Any still-real inbox or calendar action should be proposed again
only after a fresh source read.
