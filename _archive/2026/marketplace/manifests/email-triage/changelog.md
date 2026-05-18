# Changelog — email-triage

## 0.1.0 — 2026-05-04 (pilot)

- Initial SKU. Pilot tenant: alex-personal-gmail.
- 6-question onboarding interview (ICP, important people, hate-list, work hours, response style, junk definition).
- 4 categories: respond / deferred / unsubscribe / delete.
- 3 tiers: starter $49 / pro $199 / scale $999.
- BYOK: Anthropic-or-OpenAI-or-OpenRouter + Gmail OAuth.
- Trial: $5 pool, $3 nag, 7-day free week before Stripe charges.
- Eval suite: 30 golden examples, Promptfoo nightly, 85% pass-rate floor.
- A2A endpoint at `agents.prettyflyforai.com/a2a/email-triage`.
- Pilot evidence required before publish flips to true.
