---
fixture: buyer-signal-correction
expected_signal_class: reply_logged
expected_reason_code: buyer_correction
---

# Synthetic Vault State

Source: first-response-operating-packet-2026-05-17.md

- Record: synthetic-correction-001
- Reply status: correction
- Buyer language: "The drag is not reporting. It is handoff ownership after implementation."
- Named workflow: handoff ownership after implementation
- Current message angle: reporting and knowledge transfer
- Next decision under ledger rules: rewrite_message

# Expected Marin Behavior

Signal class: reply_logged.
Reason code: buyer_correction.
Allowed next action: Thank them, capture the correction, and ask one clarifying question only if useful.
Ledger update proposal should include correction summary, revised belief rung, and rewrite decision.
