# Runbook — communications-triage

## Kill switch

Disable the profile or connector account before investigating:

```bash
touch ~/.hermes/profiles/personal/PAUSED
```

## Red incidents

- Any email sent without approval.
- Any mailbox mutation applied without approval.
- Any calendar event created, changed, or deleted without approval.
- Any connector requesting a forbidden v1 write/send scope.

Response: halt the profile, revoke the affected provider token, inspect
`communications_proposals`, and add a regression test before re-enabling.
