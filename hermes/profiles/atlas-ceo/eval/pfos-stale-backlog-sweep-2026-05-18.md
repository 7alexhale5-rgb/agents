# PFOS Stale Backlog Sweep Evidence - 2026-05-18

Status: production mutation completed; no provider execution.

## Source

- Planned source packet: `atlas-atlas-ceo-1779082090175`
- Live preflight source packet: `atlas-atlas-ceo-1779082854233`
- Post-sweep source packet: `atlas-atlas-ceo-1779083021604`
- Follow-up inspection packet: `atlas-atlas-ceo-1779083037220`
- Adopted decision: `clear_pending_approval_queue_before_new_surface_area`
- Scope: exactly 20 packet-visible `pending_agent_actions` rows from the
  stale May 13 backlog
- No-mutation boundary: no actions were approved, dispatched, executed, or sent
  to providers

## Recommendation

| Recommendation | Count | Applies to |
| --- | ---: | --- |
| Approve | 0 | none |
| Reject as stale external side effect | 10 | `inbox.unsubscribe_draft` |
| Reject as stale write context | 10 | `inbox.archive`, `inbox.follow_up_task`, `inbox.reply_draft` |

## Target Rows

| Action id | Action name | Proposed at | Side-effect class | Reason |
| --- | --- | --- | --- | --- |
| `1e8a4122-b7f2-4ba2-b9e3-be1e6f58d4d2` | `inbox.follow_up_task` | 2026-05-13T20:05:18Z | write | `stale_write_context_regenerate_if_needed` |
| `208847d1-52f8-4359-aeeb-93d3d236aa4d` | `inbox.archive` | 2026-05-13T20:05:18Z | write | `stale_write_context_regenerate_if_needed` |
| `15ab448c-0980-42a0-9777-7e227b184de3` | `inbox.unsubscribe_draft` | 2026-05-13T20:05:12Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `a2f7040e-7e69-4aa6-8045-9305c17bcc97` | `inbox.unsubscribe_draft` | 2026-05-13T20:05:11Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `836c6e46-f798-4808-b22f-2a8fb8364b5c` | `inbox.unsubscribe_draft` | 2026-05-13T20:05:11Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `94d880e4-5743-4ca0-b136-9ac9d40f31c6` | `inbox.follow_up_task` | 2026-05-13T19:05:29Z | write | `stale_write_context_regenerate_if_needed` |
| `23c3a217-1b53-45ef-80e0-c514cc1cf5bd` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:26Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `e48aadce-65f8-4a41-8c33-aba5305c6420` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:24Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `31166143-a86a-47a0-908c-088b608fe8d5` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:23Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `b5cc6d72-49e4-43d1-b899-efc3191916d8` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:23Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `1d5c5242-28c4-42b6-b591-5f5814dab0a7` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:22Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `06f6780d-a0f5-4445-a7e9-2c1ed92ed55a` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:15Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `ea29b2b7-15f0-4065-b6cc-711d0a82f700` | `inbox.archive` | 2026-05-13T19:05:14Z | write | `stale_write_context_regenerate_if_needed` |
| `ce9fe0ca-f75f-44a8-b50d-88a5dfd38021` | `inbox.reply_draft` | 2026-05-13T19:05:13Z | write | `stale_write_context_regenerate_if_needed` |
| `9c4f6199-c9fe-4156-aa01-d8d63e750d63` | `inbox.unsubscribe_draft` | 2026-05-13T19:05:13Z | external | `stale_external_side_effect_regenerate_if_needed` |
| `49ad3f70-06bd-4931-a66f-4a0fea1c891d` | `inbox.archive` | 2026-05-13T18:05:32Z | write | `stale_write_context_regenerate_if_needed` |
| `f323e147-9ec6-482c-ae6d-fada9e99b694` | `inbox.reply_draft` | 2026-05-13T18:05:32Z | write | `stale_write_context_regenerate_if_needed` |
| `2d5d0657-d53b-4c37-88cd-5bd5cd8fd45a` | `inbox.archive` | 2026-05-13T18:05:28Z | write | `stale_write_context_regenerate_if_needed` |
| `78351a71-2b5e-4180-af1d-c5fc3ff2545c` | `inbox.archive` | 2026-05-13T18:05:27Z | write | `stale_write_context_regenerate_if_needed` |
| `58017948-92cd-4700-a2fe-f4b11e7d2fe1` | `inbox.archive` | 2026-05-13T18:05:27Z | write | `stale_write_context_regenerate_if_needed` |

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
| `stale_external_side_effect_regenerate_if_needed` | 10 | `inbox.unsubscribe_draft` |
| `stale_write_context_regenerate_if_needed` | 10 | `inbox.archive`, `inbox.follow_up_task`, `inbox.reply_draft` |

## Verification

- All 20 target ids now have `status=rejected`.
- All 20 target ids still have `executed_at=null`.
- Exactly 20 `agent.action.rejected` events were recorded for the target ids.
- Every rejection event has `execution_triggered=false`.
- Every rejection event has `private_payload_redacted=true`.
- Every rejection event uses the expected grouped stale-context reason.
- Re-fetched Atlas source packet no longer includes any of the 20 target ids in
  `pending_agent_actions`.

The follow-up inspection packet still reports 20 pending actions from May 13:
10 `inbox.archive`, 6 `inbox.unsubscribe_draft`, 2 `inbox.follow_up_task`,
1 `inbox.label`, and 1 `calendar.hold`. Because this is now recurring stale
residue after two packet-visible sweeps, the next lane should be a durable
stale-resolution policy or operator UX, not another manual one-off sweep.

## Evidence Event Ids

- `2c161d37-cca9-46a4-9c34-e357dda38cfb`
- `8fecbfd7-f244-46e1-a65b-f9d13fb3bfdc`
- `1806bb7c-92e1-450d-9c0d-f754b7b6a7dd`
- `98b62b4a-307f-42d1-8a9f-ff888740d1c9`
- `f6cccbf1-5fd8-471a-9de2-eaad87ff5d1d`
- `6dccffa1-19ed-46f2-aad2-ff64c12d409a`
- `c8c4cf69-07e6-488b-b70b-908712632ce8`
- `4b675028-f6ee-4adf-8108-d639bd6d5812`
- `780c5d0f-153e-48d5-ba38-ee5b773fe801`
- `83baea54-5c8d-4d7d-8c84-efa0bf169f76`
- `dba13990-5eac-4e06-9512-984e694b012a`
- `73bf8303-12b2-41a9-9d19-db25247ece4a`
- `0b60db61-abb9-46cc-a9b4-bdeaaee02f82`
- `822f9b1f-0104-4d08-9e0a-3904f44f0285`
- `638ef723-c908-418f-91d5-72cfd1d7d324`
- `b6af5d94-b641-4049-8882-31701611e5c5`
- `74e4ed14-bdd8-4198-85a1-abcdbee59f1e`
- `005cf472-64d9-4fa9-a742-50efc59ce609`
- `d13c27a8-eea8-472e-80f5-7832727742a8`
- `63d74166-a20e-4977-b31f-e331e35d31e1`

## Next Regeneration Rule

Atlas should continue treating stale queue entries as regeneration triggers, not
approval candidates. Any still-real inbox or calendar action should be proposed
again only after a fresh source read. Since the queue is still surfacing stale
May 13 residue after this second sweep, the next implementation lane should
make stale resolution explicit instead of relying on repeated operator scripts.
