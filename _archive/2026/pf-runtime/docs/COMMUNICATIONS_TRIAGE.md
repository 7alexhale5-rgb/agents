# Communications triage v1

Status: implemented scaffold, read/propose only.

## Boundary

PF Runtime owns provider normalization, proposal creation, tool dispatch, and
runtime traces. PFOS owns command surface and observability. Provider writes are
not applied in v1.

## Providers

- `google_mail`: Gmail read-only normalization.
- `google_calendar`: scope contract only in v1; event normalization lands with live OAuth.
- `microsoft_graph`: Koho Microsoft 365 mail normalization.
- `imap_hostgator`: HostGator IMAP SSL read-only normalization.
- `proposal_store`: SQLite proposals for approval review.

## Forbidden in v1

- Gmail `gmail.modify`, `gmail.compose`, `gmail.send`, or `mail.google.com`.
- Microsoft Graph `Mail.ReadWrite`, `Mail.Send`, or `Calendars.ReadWrite`.
- SMTP send.
- Calendar event write scopes.
- Any direct archive, trash, label, move, mark-read, unsubscribe, reply-send, or calendar write.

## Tool-call envelope

The loop accepts one JSON envelope for tool calls:

```json
{"tool_call":{"name":"communications.propose_action","arguments":{"action_id":"p1"}}}
```

Arguments are validated before invocation. Repeating the same tool and argument
hash more than three times in one session raises a cycle error.
