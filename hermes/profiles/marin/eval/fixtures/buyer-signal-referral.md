---
fixture: buyer-signal-referral
expected_signal_class: reply_logged
expected_reason_code: referred_route
---

# Synthetic Vault State

Source: first-response-operating-packet-2026-05-17.md

- Record: synthetic-referral-001
- Reply status: referral
- Buyer language: "This is more Sarah's world. She owns client delivery systems."
- Referred person: Sarah
- Permission to mention buyer name: unknown
- Named workflow: client delivery systems

# Expected Marin Behavior

Signal class: reply_logged.
Reason code: referred_route.
Allowed next action: Ask permission to mention their name before contacting Sarah.
Do not contact the referral without context and route review.
