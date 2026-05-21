---
name: aeo-opportunity-scout
description: Produce a source-grounded AEO/GEO opportunity memo beneath Marin, using Sentinel as prior art while staying propose-only.
input: optional topic, buyer prompt seed, or source note
output: markdown to ~/Projects/marketing/_inbox/marin-readouts/{YYYY-MM-DD}-aeo-opportunity-{slug}.md plus HTML companion
---

# Skill: aeo-opportunity-scout

## Purpose

Turn buyer-prompt and AEO/GEO research into one practical Marin memo: what prompt class to pursue, what buyer context matters, what original substance PrettyFly can use, what content/page artifact should be proposed, and how to measure it without pretending the system can publish or scale itself.

This skill ports the useful Sentinel pattern into Marin as strategy and governance:

- senses before action
- scores opportunity before content creation
- queues proposed changes for human review
- reports in plain English
- preserves human approval gates

It does not copy Sentinel runtime code from `~/Projects/yehovah/seo-agent/`, create a standalone profile, add schedulers, publish pages, send outreach, or adopt paid tools.

## Inputs (must read before producing a memo)

1. `~/Projects/marketing/brand/prettyfly-company-truth.md`
2. `~/Projects/marketing/brand/voice-and-anti-slop.md`
3. `~/Projects/marketing/offers/revenue-ladder.md`
4. `~/Projects/marketing/offers/prettyfly-ai-operations-audit.md`
5. `~/Projects/marketing/research/prettyfly-cto-advisory-icp.md`
6. `~/Projects/marketing/content/content-pillars.md`
7. `~/Projects/marketing/metrics/message-outcome-ledger-v0.md`
8. `~/Projects/marketing/metrics/marketing-tracking-plan-v0.md`
9. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md`
10. `~/Projects/marketing/decisions/2026-05-20-marketing-engine-state-of-play.md`
11. Sentinel prior art: `~/Projects/memory-vault/handoffs/2026-03-27-yeh-seo-agent-built.md` and `~/Projects/memory-vault/sessions/2026-03-27-yeh-sentinel-graceful-degradation.md`

When current-source claims are needed, cite them explicitly. Minimum current anchors:

- Google Search Central AI features: normal SEO foundations still apply; no special AI markup or `llms.txt` requirement for Google AI features.
- arXiv `2605.14021`: Google AI Overview activation/citation/fidelity measurement.
- arXiv `2604.27790`: AI Overviews/Gemini/source volatility and query sensitivity.
- arXiv `2603.29979`: content structure can affect citation behavior, but this is not a magic-content hack.
- Similarweb AI Traffic page or equivalent: AI traffic/prompts/AI referral analysis as a measurable market category.

## Required memo sections

1. **AEO opportunity** — one sentence naming the prompt class and why it belongs under Marin.
2. **Source base** — table of vault/external sources used. If a claim is not sourced, label it `assumption`.
3. **Seven-part AEO map**:
   - Stimulus: buyer-language sources and proxy inputs.
   - Buyer context: ICP, stack, vertical, team size, AI maturity, and trigger conditions.
   - Substance: PrettyFly-specific receipts, scorecard data, teardown artifacts, methodology, or advisory POV.
   - Style: voice docs and Quill/Stet review path.
   - Content creation: proposed page/content brief only; no publishing.
   - Human in the loop: Alex approval before promotion; Stet critique for public claims.
   - Analytics: Search Console, GA4 AI referral/channel group, landing-page engagement, and self-reported `AI assistant / ChatGPT / Perplexity / Google AI answer` attribution.
4. **Sentinel pattern to reuse** — name which Sentinel pattern applies: sensing, scoring, queue, report, graceful degradation.
5. **Recommendation** — one smallest next action. Default: draft one AEO opportunity memo or campaign brief in `_inbox/`, not publish.
6. **Boundaries** — no standalone profile, no `llms.txt` as primary tactic, no AI-only schema hack, no paid-tool adoption without trigger, no scale without buyer signal.
7. **Next measurement** — one metric and one stop condition.

## Decision rules

- If buyer language is missing, recommend a local prompt-seed memo or buyer-language capture step, not content production.
- If a prompt maps to a killed or deferred lane, recommend decline or defer with the trigger condition.
- If the idea depends on external search tooling, check `tool-adoption-triggers` first. Exa can be reused only under Marin's existing propose-only research boundary; new paid tools require a trigger.
- If the user asks for content/page creation, route to `campaign-brief-draft` or Quill after the memo is approved.
- If a claim would imply "Google requires `llms.txt` / special AI schema / AI-only rewrites," reject the claim and cite Google Search Central.

## Output destination

Write Markdown to:

`~/Projects/marketing/_inbox/marin-readouts/{YYYY-MM-DD}-aeo-opportunity-{slug}.md`

Render an HTML companion next to it when the memo is intended as an operator artifact.

Do not write directly to active campaign folders, offer files, ICP files, runtime publishing folders, or Sentinel/Yehovah code.

## Emit safe event summary

After the memo + HTML companion are written, run the canonical emitter so PFOS records the inbox entry:

```bash
source ~/.config/prettyfly-marketing/hermes-tokens.env
python3 ~/Projects/agents/scripts/emit-agent-event.py \
  --profile marin \
  --tool weekly_decision.propose \
  --readout-path "_inbox/marin-readouts/<YYYY-MM-DD>-aeo-opportunity-<slug>.md"
```

The event lands with `type=marin.weekly_decision.proposed`, `cwd_project=marketing`. Slug attribution is currently `weekly-review` per the tool's contract — a documented follow-up to add a dedicated `marin.aeo_opportunity.propose` tool, not a blocker. Capture the row UUID printed to stdout and include it in your response.

## Output contract for evals

Short-form eval output must follow this exact shape:

```text
AEO Opportunity Scout Memo
Source: <fixture or vault source>
Stimulus: <buyer prompt source or proxy>
Buyer context: <ICP/context fields>
Substance: <PrettyFly-specific evidence or missing-evidence note>
Style: <voice/review path>
Content creation: <proposed inbox-only artifact or hold>
HITL: <human review gate>
Analytics: <Search Console/GA4/self-reported attribution plan>
Recommendation: <one smallest next action>
Boundary: <no publish/no scale/no new tool/no standalone profile as applicable>
```

Field labels must be plain text, one per line, with values on the same line.
