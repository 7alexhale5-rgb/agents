---
date: 2026-05-20
type: decision
status: active
tags: [gmail, google-workspace, outbound, drafts, marin, decision]
parent_plan: ~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md
supersedes:
  - 2026-05-20-zapier-mcp-verdict.md
related_adrs:
  - 2026-05-18-hermes-pfos-event-contract.md
  - 2026-05-20-zapier-mcp-verdict.md
---

# Direct Google Workspace Gmail drafts for Marin

## Decision

Defer Zapier MCP for the Marin Gmail-draft pilot. Use first-party Google
Workspace / Gmail API access instead, via a narrow `marin.gmail_create_draft`
adapter that can only call `users.drafts.create`.

Zapier remains a fallback only if direct Gmail draft creation fails for a real
technical reason.

## Rationale

Alex already has Google Workspace access wired into the local Hermes
environment, and Gmail exposes an official `users.drafts.create` endpoint for
creating messages with the `DRAFT` label. Adding Zapier between Marin and
Gmail would introduce a second account surface, third-party content retention,
per-brand MCP server management, and an extra allow-list audit for a capability
the first-party API already provides.

This change preserves the doctrine:

- YAGNI: no third-party broker until the first-party path fails.
- DRY: reuse the existing Google Workspace auth/token posture.
- KISS: one draft-only adapter instead of Zapier account + MCP server + UI gate.
- SOLID: keep read-only triage separate from outbound draft creation.
- SINE: no generic Gmail tool, no send path, no cross-brand credential mixing.

## Scope

In scope:

- `marin.gmail_create_draft`
- Gmail `users.drafts.create`
- Redacted `marin.gmail_draft.proposed` PFOS event metadata
- PrettyFly Google Workspace pilot account bound outside the repo

Out of scope:

- Gmail send, draft send, reply, forward, labels, inbox mutation, or broad
  `google_api.py` exposure to Marin
- Zapier MCP server creation or consent
- Quill / Stet Gmail rollout

## Implementation Notes

The draft adapter must be separate from `hermes/shared-skills/email-triage/`.
That module intentionally refuses write-capable Gmail scopes and remains the
read/propose intake lane. Marin's Gmail draft path is a separate proposed-write
transport with one operation and one event contract.

The adapter returns raw Gmail identifiers and hashed recipient/account metadata;
PFOS events must not include body text, subject text, raw recipient addresses,
or raw target account identifiers.

## Acceptance

- Unit tests prove MIME/base64url construction.
- Unit tests prove the adapter calls `users().drafts().create(...)` and does
  not require or expose a send path.
- Marin config exposes `marin.gmail_create_draft` while keeping
  `guardrails.forbid_external_sends: true`.
- Later live check: create one harmless draft to Alex, confirm it appears in
  Gmail Drafts, and confirm the PFOS event contains only redacted metadata.
