---
fixture: buyer-signal-dogfood-current
expected_signal_class: connection_note_sent_manual
expected_reason_code: route_not_open
---

# Synthetic Vault State

Source: message-outcome-ledger-v0.md

- Records: CSpring / Jon Molendorp, Element Three / Kyler Mason, Flexware Innovation / Scott Whitlock
- Route decision: connection_note
- Connection status: not_connected for all three
- Reply status: none for all three
- Outcome: no_response for all three
- Next decision: wait_for_route for all three
- Named workflows: 0
- Diagnostics booked: 0
- WORKS Reviews offered: 0

# Expected Marin Behavior

Signal class: connection_note_sent_manual.
Reason code: route_not_open.
Allowed next action: Wait. Do not create a workaround DM.
Proposed reply: none.
