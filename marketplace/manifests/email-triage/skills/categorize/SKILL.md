---
name: categorize-email
description: Use to categorize a single incoming email into one of four buckets (respond / deferred / unsubscribe / delete) with an urgency score 1-5. Reads tenant USER.md for important_people, protect-list, hate-list. Reads tenant MEMORY.md for crystallized rules. Output is structured JSON for the orchestrator to consume.
---

# categorize-email

Single-email classifier. The orchestrator (`triage-inbox` skill) calls this once per email.

## Input

```json
{
  "subject": "string",
  "from": "string (email address)",
  "body": "string (first 2000 chars)",
  "received_at": "ISO 8601",
  "thread_age_days": "integer (0 = new thread)",
  "user_protect_list": ["string"],
  "user_important_people": ["string"],
  "user_hate_list": ["string"],
  "user_memory_rules": ["string (crystallized rules from MEMORY.md)"]
}
```

## Output (strict)

```json
{
  "category": "respond | deferred | unsubscribe | delete",
  "urgency": 1-5,
  "rationale": "≤140 chars",
  "matched_rule": "string or null"
}
```

## Decision tree

1. **Hard guards (in order — first match wins):**
   - `from` matches anyone in `user_protect_list` → `respond`, urgency 5, never delete
   - Body contains a 2FA code or verification token → `respond`, urgency 5
   - Body mentions money movement / wire / ACH / bill due / contract / signature → `respond`, urgency ≥4
   - `from` matches anyone in `user_important_people` → `respond`, urgency ≥3

2. **Pattern recognition:**
   - Known phishing patterns (urgent language + click-here + suspicious sender) → `delete`, urgency 1
   - Known marketing senders (newsletters@, marketing@, hello@somenewsletter, etc.) AND user has not opened in 30 days → `unsubscribe`, urgency 1
   - Receipt / confirmation / calendar / shipped / GitHub-notification patterns → `deferred`, urgency 1-2

3. **Apply user_memory_rules:** rules crystallized from past curation override pattern recognition (e.g., "always treat emails from acme.com as respond").

4. **Default:** if no rule fires confidently, default to `respond` urgency 3 — it's safer to over-surface than under-surface in the trial period.

## Cost

Single LLM call per email. Use the cheapest model in the routing table that handles JSON output reliably (free-rotation OpenRouter for starter; Mistral medium for pro+).

## Don't

- Never call this skill in a loop without batching — the orchestrator handles batching for cost discipline.
- Never modify the input email or the inbox state — this skill is pure classification.
- Never write to MEMORY.md from inside this skill — the orchestrator owns memory writes.
