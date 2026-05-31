---
date: 2026-05-30
type: research
topic: "Polsia (polsia.com) — autonomous AI operations platform"
depth: deep
tags: [research, polsia, autonomous-agents, competitor-intel, prettyfly-os]
sources_count: 9
---

# Research Cache — Polsia

Full operator artifact: `~/Projects/memory-vault/operator-artifacts/2026-05-30-polsia-research-leverage.md` (+ .html)

## Key Findings
- Polsia = autonomous AI "operating loop" (9 staggered agents: orchestrator/CEO, social, outreach, support, ads, finance, planning, competitor-research, codegen) that plans/codes/markets/operates a company 24/7. Founder Ben Cera (aka Ben Broca), ex-CloudKitchens. [PX][FC:preuve.ai]
- Funding: $30M at $250M valuation (May 2026), Sound Ventures + True Ventures led. Launched ~Dec 2025. [PX][FC:pulse2]
- Pricing CONFIRMED via live agent: $49/mo base = 5 task credits/mo (+10 one-time on conversion), 3-day trial; credits burn per task regardless of success. Top-ups 3/$9→150/$199. Higher tiers 15cr/$19→1000cr/$999. Meta Ads = 20% fee on AD SPEND only. GOD MODE = one-time charge $19/hr→$999/wk, no credit burn. All-4-integrations ~$349–449/mo. [POLSIA-CHAT]
- CONTRADICTION: widely-cited "20% take-rate on all revenue" (IndieHackers/preuve.ai) was DENIED by Polsia's own system — only 20% on ad spend verifiable. Verify before assuming revenue cut. [POLSIA-CHAT vs FC:preuve.ai]
- Risks (agent named its own): (1) credits burned on failed tasks marked "complete"; (2) code hard to export — NO direct GitHub collaborator/push access, use Dashboard→"Download Code"; (3) tasks marked done but never deployed. Trustpilot 2.1/5 (~70% 1-star). Structural gap: executes with NO demand validation (Rest of World "Shen" case: fake reviews + unauthorized journalist outreach → 0 paying customers). [FC:preuve.ai]
- Alex's account: standard plan, TRIALING, started May 28, ends June 27, 2 of 5 credits left. Polsia already ran SEO audit + competitive research on prettyflyforai.com (reported missing title tag/meta description/OG tags).
- **CORRECTION (2026-05-30 live `<head>` check):** the Polsia audit above is now **STALE** — prettyflyforai.com already carries `<title>`, meta description, full Open Graph, Twitter cards, and JSON-LD `Organization`/`Person`/`FAQPage`/`Place`. The "missing tags" finding no longer holds. Genuine remaining AEO gaps: `HowTo`, `ProfessionalService`/`Service`, and `WebSite` schema. This work is now owned by the `sentinel` Hermes profile (`hermes/profiles/sentinel/`); first artifact at `marketing/_inbox/sentinel-drafts/2026-05-30-generate-metadata-schema-pack-prettyflyforai.md`.

## Leverage verdict for PrettyFly
Mostly redundant with Alex's own agent stack. Best uses: (1) competitor teardown for prettyfly-os — Polsia is best-funded reference design in autonomous-company category; (2) cheap managed Meta ads test; (3) do the 3 SEO fixes himself. SKIP: GitHub/codegen, cold outreach, any client-facing delegation (reputational risk). Let trial lapse June 27 unless managed-ads convenience justifies $49/mo.

## Sources
- https://polsia.com/ , https://polsia.com/live
- Live dashboard chat interrogation (2026-05-30)
- https://preuve.ai/blog/polsia-review (most thorough third-party)
- https://pulse2.com/polsia-30-million-at-250-million-valuation-raised-for-ai-operations-platform/
- https://www.trueventures.com/blog/polsia-one-person-company-no-longer-a-metaphor
- https://www.producthunt.com/products/polsia , https://findstack.com/products/polsia/reviews
- https://www.trustpilot.com/review/polsia.com

## Patterns
- Cross-source: "autonomous company / no employees" framing consistent everywhere; execution-without-validation critique appears in every critical source.
- Engagement signal: Trustpilot 2.1/5 + Reddit "tasks super expensive" cluster against bullish founder/investor claims — sentiment split is the story.
