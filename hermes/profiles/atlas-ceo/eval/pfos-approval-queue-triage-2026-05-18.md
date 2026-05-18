# PFOS Approval Queue Triage - 2026-05-18

Status: no-mutation operator artifact.

## Evidence Header

- Source packet: `atlas-atlas-ceo-1779080714434`
- Packet generated: `2026-05-18T05:05:14.434Z`
- Source privacy: `aggregates_only_no_secrets_no_raw_private_text`
- Pending packet actions reviewed: 20
- Adopted decision: `clear_pending_approval_queue_before_new_surface_area`
- Mutation status: no PFOS action was approved, rejected, expired, dispatched,
  executed, or recreated during this artifact pass.

## Recommendation Summary

| Recommendation | Count | Rationale |
| --- | ---: | --- |
| Approve | 0 | No packet-visible row has enough fresh context to approve after aging since May 13. |
| Reject | 9 | Stale P3 promotional unsubscribe proposals are external-side-effect actions and should not be approved blindly. |
| Expire | 11 | Time-sensitive write proposals older than 4 days should be regenerated from fresh inbox/calendar state. |

## Approve

None.

## Reject

These rows are `inbox.unsubscribe_draft` proposals with external side effects.
Recommendation: reject and let any future unsubscribe be proposed from fresh
mailbox state.

| Action id | Action | Proposed at | Age bucket | Effect | Priority | Bucket | Confidence |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| `6d0a29d4-ab58-46a1-b6f2-fce45ff2c507` | `inbox.unsubscribe_draft` | `2026-05-13T22:05:15.923098+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `58c988c8-2395-40a8-888f-a6b255559720` | `inbox.unsubscribe_draft` | `2026-05-13T22:05:11.200973+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `a53209a1-e2f8-4c5f-a4a7-f58572c5f8c1` | `inbox.unsubscribe_draft` | `2026-05-13T22:05:10.449278+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `d8ab59bd-4c4f-4d94-82b0-28dac3149699` | `inbox.unsubscribe_draft` | `2026-05-13T21:05:22.942594+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `02da0224-bdac-4be0-9442-29abc7d52437` | `inbox.unsubscribe_draft` | `2026-05-13T21:05:22.306209+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `e46fc47d-877a-46c2-892e-f6cc19e7bbd5` | `inbox.unsubscribe_draft` | `2026-05-13T21:05:20.65715+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `23db8089-631e-4c54-88ec-be6f85a8ce61` | `inbox.unsubscribe_draft` | `2026-05-13T21:05:20.014214+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `e35f1e7d-3260-4ba3-b63b-698f6c7395b3` | `inbox.unsubscribe_draft` | `2026-05-13T21:05:13.437425+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |
| `629a303b-0c86-4ebe-ba3a-df3fcff13425` | `inbox.unsubscribe_draft` | `2026-05-13T21:05:12.669194+00:00` | older_than_4_days | external | P3 | promotion | 0.85 |

## Expire

These rows are stale write-class proposals. Recommendation: do not approve
them from the May 13 context; clear them as stale and regenerate only if fresh
inbox/calendar state still supports the action.

| Action id | Action | Proposed at | Age bucket | Effect | Priority | Bucket | Confidence |
| --- | --- | --- | --- | --- | --- | --- | ---: |
| `eda2f177-fb19-46bc-a063-0d3dfa48233b` | `calendar.hold` | `2026-05-13T22:05:21.182233+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `2b973d59-f3f3-434f-a0fd-7086be10d9d2` | `calendar.hold` | `2026-05-13T22:05:20.592389+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `526f1485-068a-4ec5-9e91-2b1ea5357e4b` | `calendar.hold` | `2026-05-13T22:05:20.015945+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `2697f50b-b58e-4a40-b09c-1ea406b695ac` | `calendar.hold` | `2026-05-13T22:05:19.496648+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `73e767a1-93b3-4317-96ef-2fddf74eae37` | `inbox.reply_draft` | `2026-05-13T22:05:15.325547+00:00` | older_than_4_days | write | P2 | needs_reply | 0.85 |
| `61349174-2c88-41d3-a647-75bca3bab0de` | `calendar.hold` | `2026-05-13T21:05:26.961061+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `a5c1701a-074b-4601-b03d-6f8896794b40` | `calendar.hold` | `2026-05-13T21:05:26.444015+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `3a006de2-1b05-413a-8847-439f57fa6cf7` | `inbox.follow_up_task` | `2026-05-13T21:05:21.252836+00:00` | older_than_4_days | write | P1 | needs_alex_today | 0.85 |
| `9c185ba0-8682-48b3-aac3-0c6d021c39d3` | `calendar.hold` | `2026-05-13T20:05:24.758901+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `4729120f-014f-43db-a37a-076b6e107521` | `calendar.hold` | `2026-05-13T20:05:24.195378+00:00` | older_than_4_days | write | P2 | schedule | 0.85 |
| `e7ffd2c3-7c93-42fc-8d07-97b2a6916af8` | `inbox.follow_up_task` | `2026-05-13T20:05:20.002673+00:00` | older_than_4_days | write | P1 | needs_alex_today | 0.85 |

## Next Mutation Lane

If Alex accepts this triage, handle mutation as a separate explicit PFOS pass:

- Reject the 9 stale `inbox.unsubscribe_draft` rows through the existing
  decision endpoint with a clear stale-context reason.
- Add or use an explicit stale/expired action state before clearing the 11
  expire recommendations; do not overload approval with expiration semantics.
- Re-fetch the queue after mutation and verify these 20 ids no longer block the
  packet-visible pending approval loop.
