# Email Triage — Starter Inbox Agent

> Wakes up before you do. Deletes the junk. Unsubscribes from the useless. Hands you the 5 emails that matter.

## What it does

Every morning at the time you set, this agent reads your inbox, categorizes the last 24 hours of email, and lands one digest in Slack / Telegram / your dashboard:

- **Top 5 to respond** — the only emails that needed a human eye, ranked by urgency
- **Unsubscribe queue** — drafts ready for your one-tap approval
- **Auto-archived** — everything that was just receipts, calendar pings, and confirmations

You see only what matters. The agent does the rest.

## What's in the box

|              | Starter ($49/mo)         | Pro ($199/mo)            | Scale ($999/mo)              |
| ------------ | ------------------------ | ------------------------ | ---------------------------- |
| Emails / day | 100                      | 1,000                    | unlimited                    |
| Channels     | Gmail digest             | Gmail + Slack + Telegram | unlimited                    |
| Memory       | Built-in 14 days         | + Honcho dialectic       | Full 5-axis + LoRA tuning    |
| Model floor  | OpenRouter free rotation | Mistral Medium           | Anthropic Sonnet 4.6         |
| SLA uptime   | 99.0%                    | 99.5%                    | 99.9%                        |
| Custom rules | Default + your top 3     | Default + your top 10    | Unlimited + per-domain rules |
| Trial        | $5 free pool             | $5 free pool             | $5 free pool                 |

All tiers BYOK — bring your own Anthropic / OpenAI / OpenRouter key. We charge for runtime + skills + workflow + eval SLA + observability. We don't pad token margin.

## What you provide

- A Gmail account (OAuth, your scopes only)
- A model API key (Anthropic / OpenAI / OpenRouter — your choice; cheapest works for starter)
- 6 questions answered during onboarding: ICP, important people, hate-list, work hours, response style, what counts as junk

## What we provide

- A live agent that learns your preferences week over week
- A Sunday Weekly Brief from VanClief showing this week's accuracy + cost trend
- Per-tenant kill switch you can flip from your dashboard
- 7-day pilot evidence on Alex's own Gmail (we ship nothing we haven't run on ourselves first)

## What we never do

- Send replies to humans without your tap
- Auto-unsubscribe (we draft; you tap)
- Touch email older than 30 days
- Touch email mentioning anyone on your `protect` list
- Move money, sign documents, or commit you to anything

## SLA

- Eval pass rate floor: 85% over any 7-night rolling window. If we drop below, your dashboard shows a yellow flag, our on-call gets paged, and we draft a fix PR within 24 hours.
- Action latency p95: 30 seconds from inbox arrival to digest entry.
- Kill switch: writes a `PAUSED` file to your tenant directory; halts the agent in <30 seconds.

## Pilot evidence

This SKU has run 14 days on Alex's own Gmail before reaching this catalog page. Pilot logs at `pilot-evidence/` (anonymized).

## Install

Click "Install" → Stripe checkout → 6-question interview → first digest within 5 minutes.

## Questions

`hello@prettyflyforai.com` or DM `@gregsthecode` on X.
