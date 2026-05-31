# Polsia — Competitive Intel & Steal-For-Parts

Captured 2026-05-30 from live interrogation of Polsia's dashboard (Alex's trial account) + multi-source research. Polsia is a $30M/$250M-valued "autonomous AI that runs your company" platform — a direct reference design for our own agent fleet.

**Why this lives in the agents repo:** *"Great artists steal."* Polsia's architecture maps directly onto our Hermes roster, and its failure modes are a ready-made guardrail spec. This is reference intel for building our own agents — not an endorsement of the product.

## Contents

| File | What's in it |
|---|---|
| [00-research-cache.md](00-research-cache.md) | Raw findings: what it is, funding, founder, pricing, traction, reviews |
| [01-overview-and-leverage-verdict.md](01-overview-and-leverage-verdict.md) | Full profile + how/whether to leverage it for PrettyFly (HTML companion alongside) |
| [02-architecture-teardown.md](02-architecture-teardown.md) | **The steal** — Polsia's 9-agent design mapped onto our fleet; 5 ergonomics to lift, 4 failure modes to reject |
| [03-seo-aeo-social-task-playbook.md](03-seo-aeo-social-task-playbook.md) | 10 copy-paste SEO/AEO/social task prompts (reusable as Quill/Marin skills) |

## The 60-second takeaway

- **Architecture to steal:** staggered per-agent cadence, morning+evening day-bookend, a live activity stream, atomic logged tasks, and the SEO/AEO task catalog.
- **What to reject (and why we already do):** autonomous publishing without approval, no validation gate, "complete" tasks that never shipped. Our Karpathy ladder + "Quill never publishes" is the fix — Polsia is the cautionary inverse.
- **Decision:** [`_meta/decisions/2026-05-30-polsia-competitive-intel-capture.md`](../../../_meta/decisions/2026-05-30-polsia-competitive-intel-capture.md)

## Provenance

- Polsia dashboard live chat + SEO-audit modal (Alex's account, trial ends 2026-06-27)
- Perplexity, Firecrawl, web research; best third-party source: preuve.ai/blog/polsia-review
- Source artifacts moved here 2026-05-30 from `memory-vault/operator-artifacts/` + `research-vault/research/` (consolidated per Alex's request).
