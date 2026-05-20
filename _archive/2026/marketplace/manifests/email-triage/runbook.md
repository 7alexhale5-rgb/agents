# Runbook — email-triage

## Who owns this SKU

- **Operator:** Alex (alex@prettyflyforai.com)
- **Eval auditor:** vanclief profile (Sunday Weekly Brief reports pass-rate)
- **On-call:** alex (Telegram + email at threshold breach)

## SLAs

| Metric                   | Floor  | Action if breached                                             |
| ------------------------ | ------ | -------------------------------------------------------------- |
| Eval pass rate (7-night) | 85%    | yellow flag in dashboard, page Alex, VanClief drafts fix PR    |
| Action latency p95       | 30 sec | yellow flag, investigate Composio rate limits + model provider |
| Uptime                   | 99.0%  | page Alex, fall back to text-only digest (no auto-archive)     |
| Trial-pool overrun       | $5     | hard-stop, switch tenant to BYOK-required mode                 |

## Kill switch

Tenant or operator can halt the agent for a tenant in <30 seconds:

```bash
# operator side
~/Projects/agents/scripts/seal-profile.sh email-triage-{tenant_slug}

# tenant side (dashboard toggle writes the same PAUSED file)
touch ~/.hermes/profiles/email-triage-{tenant_slug}/PAUSED
```

Resume:

```bash
~/Projects/agents/scripts/seal-profile.sh email-triage-{tenant_slug} --release
```

## Common issues + responses

### Composio rate limit (429s on Gmail OAuth)

Symptom: digest delays, action-latency p95 climbs past 30s.
Response: Composio MCP shim has retry-with-backoff; if breaches >3 windows in 24h, fall back to direct Gmail API via tenant's BYOK Google credential. Document in tenant `MEMORY.md`.

### Trial pool exhausted but tenant hasn't BYOK'd

Symptom: hard-stop at $5. Tenant emails support.
Response: Email tenant the "you've burned through the trial pool — here's how to add your model key" doc. Re-enable on key arrival.

### Eval pass rate dips below 85% for 3 nights

Symptom: yellow flag, VanClief draft PR.
Response: Pull the failing eval rows. Categorize: (a) model regression (rare, escalate), (b) tenant edge case (add to that tenant's MEMORY.md as a rule), (c) eval suite stale (update golden.jsonl to reflect new behavior). Atlas approves the fix; Codex profile builds.

### Tenant reports a wrongly-deleted important email

Symptom: tenant says "you deleted X" or "I missed Y".
Response: Pull the deletion log. Email is recoverable for 30 days in Trash. Add the sender / pattern to tenant's `MEMORY.md` `protect` list. Audit the categorization that fired and add to the eval suite as a regression case.

### Outbound approval was bypassed

Symptom: an email got SENT (vs DRAFTED) without tenant tap.
Response: This is a P0. Halt the tenant's profile via `seal-profile.sh`. Audit the trace. The guardrail layer in `~/.hermes/policies/approval.yaml` should have blocked — find the gap, write a regression test, fix.

## Escalation

- Yellow (eval slip, latency creep): VanClief Sunday Brief flag → Atlas weekly review.
- Orange (trial-pool exhaustion clustering, recurring tenant complaints): Page Alex via Telegram.
- Red (outbound bypass, kill-switch failure, billing event drift): Page Alex immediately, halt all email-triage tenants until root cause identified.

## Backup / restore

- Tenant memory snapshots run nightly to `~/Projects/_archive/2026/email-triage-snapshots/{tenant}/{date}.tgz`.
- 90-day retention.
- Restore: `tar xzf ...` into the tenant's `~/.hermes/profiles/email-triage-{tenant}/memory/` and run `sync-profile.sh push`.

## Pilot evidence

The first 14 days of running this SKU on Alex's own Gmail are at `pilot-evidence/2026-05-04-to-2026-05-18/`. That bundle is required reading before any incident response — it's the baseline of what "working" looks like.
