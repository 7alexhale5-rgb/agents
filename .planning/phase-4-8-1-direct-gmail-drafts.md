---
date: 2026-05-20
phase: 4.8.1
status: implementation-plan
title: Direct Gmail draft path for Marin
---

# Phase 4.8.1 - Direct Gmail Drafts

## Summary

Skip Zapier for the Marin draft pilot. Build one narrow Google Workspace path:
`marin.gmail_create_draft` creates Gmail drafts through `users.drafts.create`
and emits a redacted `marin.gmail_draft.proposed` event.

## Operator Flow

1. Marin produces an Alex-approved outbound draft packet.
2. `marin.gmail_create_draft` receives `to`, `subject`, `body_text`, and
   optional `body_html`.
3. The adapter builds a MIME message, base64url encodes it, and calls Gmail
   `users.drafts.create`.
4. The adapter returns Gmail draft identifiers plus hashed recipient/account
   metadata.
5. The event emitter writes one redacted PFOS row with counts and hashes only.
6. Alex reviews and sends manually from Gmail.

## Constraints

- No Zapier, MCP broker, or third-party retention surface.
- No `messages.send`, `drafts.send`, reply, forward, label, delete, archive, or
  inbox mutation.
- No changes to `email-triage`; it remains read-only.
- No raw email body, subject, recipient, or account identifier in PFOS.
- Profile env/runtime token binding stays outside the repo.

## Acceptance

- `hermes.lib.gmail_drafts` has one sanctioned public create operation.
- Marin config declares `marin.gmail_create_draft` with
  `authority: proposed_write_only`.
- Unit tests cover MIME/base64url construction, Gmail draft-create invocation,
  no send surface, config exposure, and `forbid_external_sends`.
- Live acceptance is deferred until Alex wants to create the harmless pilot
  draft in Gmail.

## Live Acceptance Status

Attempted 2026-05-20 against the existing PrettyFly `gmail-1` token. Gmail
rejected `users.drafts.create` with insufficient authentication scopes. The
available cached tokens are read-only (`gmail.readonly`); the pilot needs a
fresh Google OAuth consent for `gmail.compose` on the target PrettyFly account.
