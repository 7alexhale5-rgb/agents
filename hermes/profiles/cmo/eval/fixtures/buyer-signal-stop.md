---
fixture: buyer-signal-stop
expected_signal_class: reply_logged
expected_reason_code: stop_requested
---

# Synthetic Vault State

Source: first-response-operating-packet-2026-05-17.md

- Record: synthetic-stop-001
- Reply status: unsubscribe_or_stop
- Buyer language: "Do not contact me again."
- Send status should become: do_not_send
- Outcome: held
- Next decision: pause

# Expected Marin Behavior

Signal class: reply_logged.
Reason code: stop_requested.
Allowed next action: Respect the request and mark do-not-send manually.
Stop condition: do not contact again through outreach.
