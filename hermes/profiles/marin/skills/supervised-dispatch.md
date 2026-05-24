---
name: supervised-dispatch
description: Prepare a live-supervised LinkedIn dispatch packet for up to five Alex-approved prospects without creating unattended automation.
input: up to five approved prospect records with profile URL, route evidence, and connection-note copy
output: markdown dispatch packet plus HTML companion; no background send, scraping, scheduling, or CRM work
---

# Skill: supervised-dispatch

## Purpose

Turn an Alex-approved shortlist into a same-day supervised dispatch packet. The packet makes Chrome execution turnkey while preserving the core rule: no cron, no unattended LinkedIn sending, no scraping, no bulk tooling, and no follow-up before a route opens.

This skill does not replace `buyer-signal-router`. It only prepares the send/hold queue. After any acceptance or reply, use `buyer-signal-router`.

## Inputs (must read before preparing a packet)

1. `~/Projects/marketing/compliance/outreach-compliance-rules-v0.md`
2. `~/Projects/marketing/outreach/delivery-control-plane-v0.md`
3. `~/Projects/marketing/metrics/message-outcome-ledger-v0.md`
4. The source review packet or shortlist named by Alex
5. Active campaign README, currently `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/README.md`
6. `DOCTRINE.md` and `MEMORY.md`

## Hard Limits

- Maximum five prospects per dispatch packet.
- Maximum 15-16 sent LinkedIn connection notes in a week unless a route opens and Alex explicitly approves continuing.
- No unattended daily run, cron, browser loop, sequencer, scraper, Unipile, Apollo bulk action, CRM write, dashboard build, cold email, paid ad, profile-like/comment behavior, or workaround DM.
- Stop immediately on LinkedIn warning, CAPTCHA, 2FA, invitation limit, UI restriction, unusual login challenge, or route mismatch.
- If note text exceeds 300 characters, mark the row `hold_rewrite`.
- If current role/company cannot be verified in the live browser, mark the row `hold_route_unverified`.

## Procedure

1. **Source pass** — read the ledger, control plane, compliance note, and source packet. Record current total sent this week, pending notes, accepted notes, replies, and holds.
2. **Input check** — reject the packet if it has more than five prospects or lacks exact profile URLs and exact note copy.
3. **Route check** — for each prospect, verify profile URL, current company/role, connection status, route reason, and whether the proposed note matches the current-company route.
4. **Decision** — choose exactly one row decision:
   - `send_ready`: Alex approved the exact route and note; live supervised send may proceed.
   - `already_sent_wait`: note was already sent; wait for acceptance or reply.
   - `hold_route_unverified`: current role/company/route is not verified.
   - `hold_past_company`: route depends on a past company, not the current buyer route.
   - `hold_rewrite`: note is too long, too salesy, or mismatched.
   - `blocked_account_health`: LinkedIn warning, challenge, or limit appeared.
5. **Operator packet** — write a markdown source and HTML companion when Alex asks for an artifact. Include totals, per-row status, exact notes, profile URLs, and stop conditions.
6. **Live session rule** — if Alex asks for live execution, open each `send_ready` profile and prepare the send path. The final send is allowed only inside that live approved session. Do not run later in the background.
7. **Ledger proposal** — after any live send, propose ledger updates with `send_status=sent_manual`, the date, approved message reference, and `next_decision=wait_for_route`.

## Output shape

Every dispatch packet must include:

- title and date
- source files read
- current totals: sent, pending, accepted, replied, held
- account-health gate
- daily and weekly caps
- table with prospect, profile URL, current role/company, route reason, note character count, decision, and stop condition
- exact note copy for every `send_ready` row
- next 1% move

## Safety language

Use this exact safety statement in every packet:

```text
This packet does not authorize unattended LinkedIn automation. It authorizes only a live supervised session using Alex-approved prospects and notes. Stop on any LinkedIn warning, challenge, limit, route mismatch, or request to scale volume without route learning.
```
