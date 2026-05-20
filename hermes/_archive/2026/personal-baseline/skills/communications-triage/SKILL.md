---
name: communications-triage
description: Unified read/propose triage for Alex's Gmail, Microsoft 365, HostGator mail, and calendars.
dependencies:
  - pf-runtime.communications
---

# Communications Triage

Use this skill when Alex asks for mail triage, calendar triage, morning brief,
or a unified priority view across Gmail, Microsoft 365, HostGator mail, and
calendar accounts.

## V1 Policy

- Read and rank mail/calendar items.
- Propose labels, archives, folder moves, trash, unsubscribe drafts, reply drafts,
  calendar holds, calendar edits, and follow-up tasks.
- Never apply a mailbox or calendar mutation directly.
- Never send email.
- Never request Gmail `gmail.modify`, Microsoft Graph `Mail.ReadWrite`, SMTP send,
  or calendar write scopes for v1.

## Output

Return a concise digest:

1. Needs Alex today
2. Schedule risks
3. Needs reply
4. Waiting / FYI
5. Promotions, releases, updates, and noise
6. Proposed actions awaiting approval
