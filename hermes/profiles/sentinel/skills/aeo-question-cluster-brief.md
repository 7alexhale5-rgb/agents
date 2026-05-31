---
name: aeo-question-cluster-brief
description: Research the top 20 real-buyer questions about AI operations advisory for service businesses from PAA, Reddit, and industry forums. Cluster into 4 content hubs. Produce one answer-first content brief with question-shaped H2s and 40-60 word extractable answer drafts ready for AI Overview / Perplexity citation. Propose-only — writes to _inbox/sentinel-drafts/, never touches the live site.
input: optional `focus_angle` string (e.g. "workflow automation" or "WORKS Review"); defaults to "AI operations advisory for service businesses"
output: one markdown brief at ~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-aeo-question-cluster-brief-{slug}.md + Hermes local receipt
---

# Skill: aeo-question-cluster-brief

## Purpose

Produce one answer-first content brief (question-shaped H2s + 40-60 word extractable answer drafts) derived from People-Also-Ask, Reddit, and industry forum research. The brief gives Alex a ready-to-use page or section outline that AI answer engines (Google AI Overviews, Perplexity, ChatGPT) can quote directly once the content is live.

Success metric: each H2 maps to a documented buyer question source; each answer draft is self-contained, factually grounded in vault files, and under 60 words so an AI system can quote it without context. The brief is paste-ready — Alex deploys it; Sentinel never does.

## Inputs (must read in this order before generating)

1. `DOCTRINE.md` — the VERIFY-THEN-DEPLOY gate, banned tactics, AEO decision rules, and output contract frontmatter
2. `MEMORY.md` — current audit gaps and any prior AEO question-cluster work already completed
3. `USER.md` — site positioning, ICP, and current priority pages for prettyflyforai.com
4. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts, offer names, working values; no claim about PrettyFly without anchoring here
5. `~/Projects/marketing/brand/voice-and-anti-slop.md` — banned vocab, voice spine; answer drafts must pass this filter
6. `~/Projects/agents/docs/competitive-intel/polsia/03-seo-aeo-social-task-playbook.md` — task #3 prompt shape and hub-cluster model
7. `DOCTRINE.md § Canonical source anchors` — cite `arXiv 2603.29979` when making content-structure claims; cite `arXiv 2605.14021` when referencing AI Overview citation behavior

## Procedure

1. **Confirm no duplicate.** Check `MEMORY.md` and `~/Projects/marketing/_inbox/sentinel-drafts/` for any prior AEO question-cluster brief. If one exists from within the last 30 days on the same `focus_angle`, surface it and hold — do not burn a run re-generating the same artifact. If no recent prior, continue.

2. **Derive the research scope.** From `USER.md` and `prettyfly-company-truth.md`, identify the site positioning string (default: "Workflow-First AI Operations & Systems Advisory for service businesses") and the `focus_angle` input. The research query is: `"{focus_angle} for service businesses"` plus variants on buyer pain points found in the company-truth file.

3. **Collect 20 real buyer questions.** Use web search (Firecrawl MCP or WebFetch) to surface People-Also-Ask (PAA) entries, Reddit threads (r/smallbusiness, r/entrepreneur, r/aitools), and industry forum posts for the research scope. Do not invent questions. For each question record:
   - The question text verbatim (or lightly cleaned)
   - Source (PAA / Reddit / forum, with URL or citation reference)
   - Approximate buyer stage (awareness / evaluation / decision)

   If search results return fewer than 20 distinct questions, document what was found, mark the gap, and continue with available questions rather than fabricating additional ones.

4. **Cluster into 4 content hubs.** Group the 20 questions into 4 thematic hubs. Hub labels should map to buyer-journey stages or distinct pain-point clusters, not keyword buckets. Name each hub plainly (e.g., "What AI operations advisory is and who it's for", "How the WORKS Review process works", "What changes after an AI Ops engagement", "How to evaluate AI advisory providers"). Each hub must contain at least 3 questions.

5. **Draft answer-first H2 + extractable answer for each question.** For each of the 20 questions:
   - **H2**: rephrase the question as a natural-language heading that matches how a buyer or AI system would ask it. No keyword stuffing. Example: "How does PrettyFly's WORKS Review identify workflow drag?" not "WORKS Review workflow drag identification service."
   - **Extractable answer**: 40-60 words. Answer the question directly in the first sentence. No preamble ("Great question…", "It depends…"). Ground every factual claim in `prettyfly-company-truth.md` or a cited source. Ends with one concrete next step or observable outcome. Passes the voice-and-anti-slop banned vocab filter.

6. **Apply voice-and-anti-slop filter.** Run all 20 answer drafts against the banned vocab list from `voice-and-anti-slop.md`. Any hit on "leverage / 10x / moat / compound / unlock / next-level / game-changing / AI-powered / revolutionary / crushing it" requires a rewrite before writing the output file. One sweep; document any rewritten lines.

7. **Draft schema annotation block.** After the question clusters, append one `FAQPage` JSON-LD stub covering the top 5 questions (highest-traffic or highest-buyer-intent, your judgment). This is a draft — it is not validated. Mark it `<!-- DRAFT: validate at https://search.google.com/test/rich-results before deploying -->`. Do not include fake `datePublished` or inflated `answerCount` fields — only factually accurate attributes. Cite `DOCTRINE.md § AEO = normal SEO + structure` as the rationale.

8. **Append measurement plan.** After the schema block, add a `## Measurement` section with three concrete checks Alex performs after deploying the content:
   - GSC: monitor "rich results" report for FAQPage eligibility within 14 days of index.
   - GA4: track sessions in the AI-referral channel group to the page where this content lands; baseline vs. 30-day post-deploy delta.
   - Manual spot-check: query the top 3 H2 questions verbatim in Perplexity and note whether prettyflyforai.com appears in citations. Record baseline before deploy.
   Cite `DOCTRINE.md § Measurement doctrine` as the source for these metrics.

9. **Write the output file.** Write exactly one file to:
   `~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-aeo-question-cluster-brief-{slug}.md`
   where `{slug}` is a 2-4 word kebab-case label derived from the `focus_angle` (e.g. `ai-ops-advisory`, `works-review-process`). Use the frontmatter from `DOCTRINE.md § Output contract`:

   ```yaml
   ---
   date: {YYYY-MM-DD}
   type: sentinel-draft
   status: proposed
   project: prettyflyforai-seo-aeo
   skill: aeo-question-cluster-brief
   agent: sentinel
   site: prettyflyforai.com
   audit_gap: aeo-content-coverage
   impact: high
   effort: medium
   verify_after_deploy: "run GSC Rich Results Test on target page; spot-check top 3 H2s in Perplexity"
   private_payload_redacted: true
   source_questions_count: {N}
   hubs_count: 4
   schema_stub: true
   ---
   ```

   Body structure:
   ```
   # AEO Question-Cluster Brief — {focus_angle}

   > **Scope:** {site positioning string} · **Date:** {YYYY-MM-DD}
   > **How to use:** paste one hub at a time into the relevant page or new guide page. Deploy yourself — do not send to Sentinel for auto-deploy.

   ## Research Notes
   [brief summary of sources used, number of PAA vs Reddit vs forum questions, any gaps]

   ## Hub 1: {hub label}
   ### {Question-shaped H2}
   {40-60 word extractable answer}
   *Source: {PAA URL or Reddit thread ref}*

   [repeat for each question in hub]

   ## Hub 2: {hub label}
   ...

   ## Hub 3: {hub label}
   ...

   ## Hub 4: {hub label}
   ...

   ## Schema Stub (FAQPage — top 5 questions)
   <!-- DRAFT: validate at https://search.google.com/test/rich-results before deploying -->
   {JSON-LD block}

   ## Measurement
   {three measurement checks from step 8}
   ```

10. **Emit Hermes local receipt.** After the file is written, emit a `sentinel.draft.proposed` event per `DOCTRINE.md § Output contract`:
    `type=sentinel.draft.proposed`, `status=pending`, `surface=cli`, `cwd_project=marketing`, `skill_slug=aeo-question-cluster-brief`, `data.runtime=hermes`, `data.proposal_status=proposed`, `data.private_payload_redacted=true`. Receipt may include impact, effort, hubs count, question count, and vault-relative draft path. It must not include raw scraped content, full answer drafts, or any private source text. Confirm the receipt exists and capture the receipt ID into the brief's footer as `receipt_id: {uuid}`.

## Validation checklist

Before marking this skill run complete, confirm every item below is true. A `NO` on any item means the skill run is incomplete — do not emit the receipt until all pass.

| # | Check | Pass? |
|---|---|---|
| 1 | Output file exists at the exact path pattern `_inbox/sentinel-drafts/YYYY-MM-DD-aeo-question-cluster-brief-{slug}.md` | — |
| 2 | All 20 question sources are cited (PAA URL, Reddit thread, or forum ref) — no invented questions | — |
| 3 | Each of the 4 hubs contains at least 3 questions | — |
| 4 | Every extractable answer is 40-60 words (count if uncertain) | — |
| 5 | Every factual claim about PrettyFly traces to `prettyfly-company-truth.md` | — |
| 6 | Voice-and-anti-slop banned vocab sweep passed (no hits remaining) | — |
| 7 | FAQPage JSON-LD stub is marked as DRAFT with validator URL | — |
| 8 | Measurement section references GSC, GA4 AI-referral, and manual Perplexity spot-check | — |
| 9 | Frontmatter includes all required DOCTRINE.md fields with accurate values | — |
| 10 | Hermes local receipt emitted with `skill_slug=aeo-question-cluster-brief` and `data.private_payload_redacted=true` | — |

## No-external-side-effects gate

**This skill MUST NOT:**
- Write to any file outside `~/Projects/marketing/_inbox/sentinel-drafts/`
- Edit, commit to, or PR against the prettyflyforai.com codebase or any other repo
- Post, publish, or schedule any content to any platform
- Deploy schema, metadata, or copy to the live site
- Invoke any paid API or tool not already authorized in `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md`
- Run autonomous crawlers or monitors beyond the single research pass in step 3

If any of the above would be triggered by completing a step, stop, surface the conflict to Alex, and hold. Do not work around the gate.
