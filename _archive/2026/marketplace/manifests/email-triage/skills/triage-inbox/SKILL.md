---
name: triage-inbox
description: Use to triage an entire inbox window (last 24h by default). Reads emails via the Composio Gmail MCP, calls categorize-email per message, archives deferred, deletes junk, drafts unsubscribes for tenant approval, and produces a 3-section digest. Writes a summary entry to MEMORY.md.
---

# triage-inbox

Orchestrator skill. Runs daily on cron OR on tenant demand.

## When this fires

- Cron: `0 6 * * *` daily at 06:00 tenant-local time
- On-demand: tenant says "triage my inbox" via Telegram / dashboard / Slack DM

## Steps

1. **Read input** — pull `lookback_hours` (default 24) and `tenant_slug` from invocation. Read `tenant/USER.md` for protect/important/hate lists. Read `tenant/MEMORY.md` for crystallized rules.

2. **Fetch emails** — Composio Gmail MCP: `gmail.list_messages(query="in:inbox newer_than:24h", max=200)`. If pro/scale tier, no cap. Starter cap is 100 emails/day; if exceeded, batch and resume tomorrow.

3. **Batch categorize** — group emails by sender domain to maximize cache hits on the categorizer prompt. Call `categorize-email` skill for each group. Cost discipline: free-rotation model handles ~95% of cases; escalate to Sonnet ONLY when the categorizer returns `confidence < 0.7`.

4. **Apply actions:**
   - `delete` → `gmail.move_to_trash(message_id)` — recoverable for 30 days
   - `unsubscribe` → DO NOT auto-unsubscribe. Use the List-Unsubscribe header to draft an unsubscribe message; queue in `tenant/workspace/unsubscribe-queue.json` for tenant approval
   - `deferred` → `gmail.archive(message_id)` — keeps in All Mail, removes from inbox
   - `respond` → leave in inbox, surface in digest

5. **Compose digest:**

```markdown
# Email Triage — {date} {time}

## 📬 Top {N} to respond ({total} respond-flagged, {N} shown)

1. **From {sender}** — {subject}
   {1-line rationale} · {suggested CTA}
2. ...

## 🔕 Unsubscribe queue ({count} drafts ready)

[View queue]({dashboard_url}/unsubscribe-queue)

## ✅ Auto-archived

{N_deferred} deferred · {N_deleted} deleted (recoverable in Trash for 30 days)
```

6. **Send digest** — Telegram (short version: top 3 + counts) AND Gmail (long version) AND dashboard.

7. **Persist:**
   - Write a single line to `tenant/MEMORY.md` summarizing today's triage
   - If a recurring sender appeared in `respond` for 7 days running, add to `important_people` (with tenant note in next digest)
   - If a recurring sender appeared in `delete` for 7 days running, add to a "junk_senders" rule in `MEMORY.md`

## Guardrails

- **Outbound approval enforced** — unsubscribe sends require tenant tap, never auto-fire
- **PII redaction** in digest text — the digest renders to channels that may not have the same security boundary as the inbox itself
- **Spend cap** — if the day's LLM spend exceeds tier limit, halt processing and digest only what was processed; alert the tenant

## Failure modes

- **Composio rate limit:** retry with backoff up to 3 times; on 4th failure, email tenant "triage delayed, will retry next cron"
- **Gmail quota:** if the OAuth scope is throttled, fall back to a smaller batch and resume next run
- **Categorizer disagreement** (the 5% where the model returns ambiguous output): leave email in inbox, note in digest as "needs review"

## Don't

- Never delete email older than 30 days from the operating window
- Never send unsubscribes without tenant approval
- Never apply categorization rules that aren't in the tenant's `MEMORY.md` or the global default tree
- Never touch the protect-list senders even if pattern recognition says junk

## Cost target

≤$0.05 per 100 emails on starter. ≤$0.20 per 100 on pro (Mistral medium handles edge cases). Scale tier scales with tenant volume.
