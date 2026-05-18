---
name: buyer-signal-router
description: Route a buyer signal into the next allowed manual action without creating automation, CRM, PFOS, or outreach-volume work.
input: one buyer signal or ledger state from the active PrettyFly AI Ops Audit loop
output: proposed next-action memo; inline by default, or markdown to ~/Projects/marketing/_inbox/cmo-readouts/{YYYY-MM-DD}-buyer-signal-{slug}.md if requested
---

# Skill: buyer-signal-router

## Purpose

Turn a route opening, reply, correction, referral, rejection, or no-reply state into one allowed next action. This is Marin's intake nerve: it protects the loop from scaling before buyer workflow signal exists.

This skill does not create a new profile, CRM, PFOS screen, outreach automation, cold email path, Unipile workflow, bulk Apollo run, Quill draft, or Viper critique. It classifies the signal and proposes the next manual move.

## Inputs (must read before routing)

1. `~/Projects/marketing/metrics/message-outcome-ledger-v0.md`
2. `~/Projects/marketing/outreach/delivery-control-plane-v0.md`
3. `~/Projects/marketing/outreach/first-response-operating-packet-2026-05-17.md`
4. `~/Projects/marketing/metrics/weekly-revenue-loop-v0.md`
5. Active campaign README, currently `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/README.md`
6. `DOCTRINE.md` and `MEMORY.md`

## Signal routing table

Use the signal classes and reason codes from the First Response Operating Packet.

| Input state | Signal class | Reason code | Allowed next action |
| --- | --- | --- | --- |
| No acceptance and no reply | `connection_note_sent_manual` | `route_not_open` | Wait. Do not create a workaround DM. |
| Accepted connection, no reply | `connection_accepted` | `route_opened` | Alex may send one approved post-acceptance workflow-question DM manually. |
| Positive reply | `reply_logged` | `qualified_interest` | Ask one diagnostic question. Mention WORKS Review only after a real workflow is named or the buyer asks what it includes. |
| Correction | `reply_logged` | `buyer_correction` | Thank them, capture the correction, and ask one clarifying question only if useful. |
| Referral | `reply_logged` | `referred_route` | Ask permission to mention their name before contacting the referral. |
| Not relevant | `reply_logged` | `wrong_fit` | Acknowledge and close the loop. |
| Negative reply | `reply_logged` | `negative_response` | Apologize once if useful and stop. |
| Stop request | `reply_logged` | `stop_requested` | Respect the request and mark do-not-send manually. |
| Content engagement only | `reply_logged` | `weak_engagement` | Log only if tied to a named prospect or ICP learning; do not treat as buying intent. |
| Website or email inbound | `reply_logged` | `inbound_interest` | Qualify against ICP, pain, urgency, and service fit. |

## Procedure

1. **Source pass** — identify the ledger record, signal source, date, company/person, current route status, reply status, outcome, and next decision. If a value is missing, write `unknown` rather than guessing.
2. **Classify** — choose exactly one signal class and one reason code from the table above.
3. **Workflow gate** — decide whether a named workflow exists. If the source says `Named workflow: <specific workflow>` or the buyer clearly names/validates a workflow, copy that workflow exactly. If the source says `Named workflows: 0` or no workflow is present, write `Named workflow: none` and do not recommend WORKS Review, diagnostic CTA, content scaling, channel scaling, or automation. Approved message names, DM labels, message refs, and "workflow-question DM" artifacts are not workflows.
4. **Allowed action** — choose exactly one next manual action from the First Response Operating Packet or Weekly Revenue Loop Manual Action Menu.
5. **Reply proposal gate** — include a proposed reply only when the route has opened. If the route is still closed, write `Proposed reply: none`. Keep this field to `none`, an exact approved vault message reference, or a one-sentence manual reply intent; do not draft polished copy.
6. **Ledger proposal** — name the ledger fields Alex should update. Do not write the ledger directly.
7. **Client-health check** — add a warning if the action would crowd out active Koho or Yehovah obligations. Default to `no client-health conflict identified` when no evidence suggests crowd-out.
8. **Stop condition** — name the condition that stops all follow-up.
9. **Safety check** — confirm the memo does not recommend sending, publishing, automating, scraping, scaling, changing systems, or adopting tools without human approval.

## Output shape

Use plain text only. The first line is exactly `Buyer Signal Router Memo`. Every field label below appears exactly once, with the value on the same line. Do not use Markdown headings, bold labels, bullets inside fields, escaped underscores, or prose-wrapped labels.

```text
Buyer Signal Router Memo
Source: <vault file(s)>
Record: <ledger id or prospect/company/person>
Route status: <route_not_open | route_opened | reply_logged | unknown>
Signal class: <signal class>
Reason code: <reason code>
Named workflow: <workflow or none>
Allowed next action: <one manual action>
Proposed reply: <one approved/manual-only reply, or none>
Ledger update proposal: <fields Alex should update manually>
Stop condition: <one condition>
Client-health warning: <warning or no client-health conflict identified>
Safety check: no automation, no external send, no PFOS/CRM/tooling work, no volume increase without human approval.
```

## Dogfood baseline

For the current first three live connection notes, all still `not_connected` with `reply_status: none`, the correct output is:

- `Signal class: connection_note_sent_manual`
- `Reason code: route_not_open`
- `Named workflow: none`
- `Allowed next action: Wait. Do not create a workaround DM.`
- `Proposed reply: none`

## Anti-patterns to avoid

- Treating an acceptance as permission to pitch WORKS Review
- Treating an approved DM, approved message reference, or workflow-question DM label as a named workflow
- Treating generic curiosity, likes, or profile views as buyer workflow signal
- Recommending follow-up when the route has not opened
- Recommending automation, Unipile, cold email, paid ads, CRM, PFOS, bulk Apollo, website publishing, or more outreach volume
- Updating the message ledger directly
- Collapsing referral, correction, negative reply, and stop request into the same "reply" bucket
- Asking more than one next question in a proposed reply
