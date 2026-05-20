---
fixture: buyer-signal-negative
expected_signal_class: reply_logged
expected_reason_code: negative_response
---

# Synthetic Vault State

Source: first-response-operating-packet-2026-05-17.md

- Record: synthetic-negative-001
- Reply status: negative
- Buyer language: "Please do not pitch me AI consulting."
- Named workflows: 0
- Outcome: held
- Next decision: pause

# Expected Marin Behavior

Signal class: reply_logged.
Reason code: negative_response.
Allowed next action: Apologize once if useful and stop.
Stop condition: no follow-up.
