---
name: competitor-citation-teardown
description: For a given set of target queries, document which pages ChatGPT and Perplexity currently cite, then produce a structured comparison table and the exact structural changes prettyflyforai.com must copy to win those citations. Propose-only — writes one markdown artifact to _inbox/sentinel-drafts/. Never edits the live site or opens a PR.
input: required `queries` (list of 3-7 target queries); optional `slug` (kebab-case label for the output filename, defaults to first query kebab-ized)
output: one markdown file at ~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-competitor-citation-teardown-{slug}.md + safe Hermes local receipt
---

# Skill: competitor-citation-teardown

## Purpose

Identify which competitor pages ChatGPT and Perplexity cite for prettyflyforai.com's highest-value target queries, reverse-engineer the structural signals that earned those citations, and produce a paste-ready action list Alex can apply himself. This is the execution of Polsia task #4 adapted for Sentinel's verify-then-deploy contract (source: `agents/docs/competitive-intel/polsia/03-seo-aeo-social-task-playbook.md` §4).

Success metric: every cited page is documented with ≥5 structural dimensions; every recommendation traces to an observed gap between the cited page and prettyflyforai.com; no claim is invented.

## Inputs (must read in this order before beginning)

1. `hermes/profiles/sentinel/DOCTRINE.md` — VERIFY-THEN-DEPLOY gate, banned tactics, AEO decision rules, measurement doctrine, and output contract (frontmatter shape)
2. `hermes/profiles/sentinel/MEMORY.md` — known audit gaps (title/meta/OG status, HIGH-risk items) and prior teardown runs if any
3. `hermes/profiles/sentinel/USER.md` — site positioning and ICP for prettyflyforai.com
4. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts, offer names, and proof points (needed to assess entity consistency in cited pages vs. our own)
5. `~/Projects/marketing/brand/voice-and-anti-slop.md` — for any copy observations in the action list (ensure recommendations do not produce banned vocab)
6. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md` — do not recommend a new paid tool unless the trigger is already met

## Procedure

### Phase 1 — Probe ChatGPT and Perplexity for each query

1. For each query in `queries`, submit it verbatim to ChatGPT (GPT-4o or latest available via `claude-in-chrome` MCP or manual browser session) and to Perplexity. Capture:
   - The full answer text
   - Every URL cited in footnotes / sources panel
   - Whether prettyflyforai.com appears in the citations (yes / no / partial)

2. If browser access is unavailable for one engine, note the gap in the artifact and proceed with the other engine rather than blocking. Do not invent citations.

3. Record raw citation data per query in a scratch table (not in the final artifact) before moving to Phase 2.

### Phase 2 — Crawl and analyze each cited page

4. For each unique cited URL (up to 5 per query, deduplicated across queries), crawl the page using Firecrawl MCP (`firecrawl_scrape`) or the stealth-fetch escalation chain if Firecrawl returns empty. Capture per page:

   | Dimension | What to extract |
   |---|---|
   | **Answer-first block** | Does the page open with a 1-3 sentence direct answer to the target question? (yes / no / approximate word count of the opening block) |
   | **Heading format** | Are H2/H3s phrased as questions? List the first 3 H2s verbatim. |
   | **Schema present** | List all JSON-LD `@type` values found (FAQPage, HowTo, Article, Organization, etc.) |
   | **Word count** | Approximate body word count |
   | **FAQ block** | Does the page contain a visible FAQ section? (yes / no; question count if yes) |
   | **Entity signals** | Is the brand name consistent with its known canonical form? (note any variant spellings) |
   | **Internal links** | Approximate count of internal links from this page |

5. For each crawled page, note whether prettyflyforai.com has an equivalent page targeting the same query. If yes, crawl that page too and record the same 7 dimensions for direct comparison. Use `MEMORY.md` known gaps to short-circuit obvious misses (e.g., if OG tags are known MISSING, note that without re-crawling the homepage for every query).

### Phase 3 — Score and prioritize gaps

6. For each query, compare the top-cited competitor page vs. the prettyflyforai.com equivalent (or note "no equivalent page exists"). Produce a gap score for each dimension:
   - **0** = we match or exceed the cited page on this dimension
   - **1** = minor gap (present but weaker)
   - **2** = significant gap (absent or clearly worse)

7. Sum each gap dimension across all queries to produce a priority rank: dimensions with the highest total score across queries are the highest-leverage structural changes.

### Phase 4 — Draft the artifact

8. Write the artifact to `~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-competitor-citation-teardown-{slug}.md` with the frontmatter from `DOCTRINE.md § Output contract`:

   ```yaml
   ---
   date: {YYYY-MM-DD}
   type: sentinel-draft
   status: proposed
   project: prettyflyforai-seo-aeo
   skill: competitor-citation-teardown
   agent: sentinel
   site: prettyflyforai.com
   audit_gap: citation-gap
   impact: {high | medium | low}
   effort: {high | medium | low}
   verify_after_deploy: "re-run this skill after implementing the top 3 structural changes; check GA4 AI-referral channel group for citation-attributed sessions within 30 days"
   private_payload_redacted: true
   queries_tested: [{list of queries}]
   engines_tested: [{ChatGPT | Perplexity | both}]
   ---
   ```

9. The artifact body must contain exactly these sections in order:

   **## Summary** (3-5 sentences): How many queries were tested, how many cited prettyflyforai.com, and the top-line finding. Example shape: "Tested 5 queries across ChatGPT and Perplexity. prettyflyforai.com was cited 0/5 times. The primary structural gap is the absence of answer-first opening blocks and FAQPage schema, present in 4/5 top-cited pages."

   **## Citation map** (table): One row per query × engine combination.

   | Query | Engine | Top cited URL | Our page cited? | Our equivalent URL |
   |---|---|---|---|---|
   | ... | ... | ... | yes / no | ... |

   **## Cited page structure** (one sub-section per unique cited URL, max 5 per query, deduplicated): Each sub-section heading is the domain name (not the full URL, to avoid exposing sensitive paths). Body: the 7 dimensions from Step 4 as a compact table. Source the URL in the frontmatter, not inline in the heading. Cite the crawl date in each sub-section footer.

   **## Gap table** (scored): Dimensions × queries, gap scores from Step 6.

   | Dimension | Priority score (sum across queries) | Our current state | Cited page standard |
   |---|---|---|---|
   | Answer-first block | ... | ... | ... |
   | Question-shaped headings | ... | ... | ... |
   | FAQPage schema | ... | ... | ... |
   | Word count | ... | ... | ... |
   | HowTo schema | ... | ... | ... |
   | Entity consistency | ... | ... | ... |
   | Internal links | ... | ... | ... |

   **## Structural changes to implement** (numbered, ordered by priority score, max 10): Each item is a specific, paste-ready instruction. Format per item:

   ```
   N. {ACTION VERB in all caps}: {one sentence describing the change}
      - Target page: {URL or "new page needed"}
      - Source evidence: {domain of cited page} — {specific dimension that earned citation}
      - Implementation: {what to write/add/restructure — enough detail for Alex to act without re-reading this artifact}
      - Effort: {high | medium | low}
   ```

   Do not include vague items like "improve content quality." Every item must be a falsifiable structural change (add FAQPage schema, restructure opening paragraph to answer-first, add question-shaped H2s, etc.).

   **## What to measure after deploy** (3-5 bullet points): Specific GSC queries or GA4 AI-referral channel checks that would confirm the change is working. Reference DOCTRINE.md measurement doctrine. Include the expected signal and the timeframe.

### Phase 5 — Emit Hermes local receipt and validate

10. Confirm the file exists at the target path before emitting the receipt.

11. Emit a safe `sentinel.draft.proposed` Hermes local receipt per `DOCTRINE.md § Output contract`: `type=sentinel.draft.proposed`, `status=pending`, `surface=cli`, `cwd_project=marketing`, `skill_slug=competitor-citation-teardown`, `data.runtime=hermes`, `data.proposal_status=proposed`, `data.private_payload_redacted=true`. Receipt may include: impact, effort, queries_tested count, engines_tested, vault-relative draft path. Must not include raw crawled page source, full HTML, or scraped private content.

12. Record the receipt ID in the artifact footer as `receipt_id: {uuid}`.

## Validation checklist

Before marking this skill run complete, verify every item:

- [ ] All queries in `queries` input were tested against at least one engine; any skipped queries are documented with reason
- [ ] Every cited URL was crawled (or crawl failure noted with reason); no citations are invented
- [ ] Every structural claim in the Gap table traces to observed page data, not assumption
- [ ] The Structural changes section contains only falsifiable, specific changes — no vague recommendations
- [ ] Frontmatter is complete and matches `DOCTRINE.md § Output contract` shape
- [ ] Artifact is written to `~/Projects/marketing/_inbox/sentinel-drafts/` and nowhere else
- [ ] No edits were made to the live site, any repo, or any file outside `_inbox/sentinel-drafts/`
- [ ] Hermes local receipt emitted with `private_payload_redacted: true`
- [ ] Receipt ID recorded in artifact footer

## No-external-side-effects gate

This skill is PROPOSE-ONLY. It MUST NOT:

- Write to, edit, or deploy any file on prettyflyforai.com
- Open a GitHub PR or push a commit to any repository
- Post to any social channel, CMS, or DNS record
- Send any email, Slack message, or notification outside the Hermes local receipt
- Schedule any recurring crawl, monitor, or cron job
- Call any paid API not already authorized in `tool-adoption-triggers`

If any of the above would be required to complete a step, halt and surface the blocker to Alex instead.

## AEO structural best practices encoded in this skill

The 7 dimensions in Phase 2 and the Gap table map directly to the structural levers that affect AI answer engine citation behavior, per the canonical sources in `DOCTRINE.md`:

- **Answer-first blocks**: 40-60 word direct answers the AI can quote without context (arXiv 2603.29979)
- **Question-shaped headings**: H2/H3s matching the query as a user would ask it — improves extractability
- **FAQPage / HowTo / Article schema**: Machine-readable structured data that makes content citation-eligible; must match visible page content
- **Entity consistency**: Canonical brand name across all surfaces — required for "PrettyFly" / "PrettyFly.ai" / "prettyflyforai.com" to resolve to one entity in AI knowledge graphs
- **Measurement via GSC + GA4 AI-referral**: The only non-vanity measurement path available without a paid tool trigger

Schema is not magic. Structural changes earn citations because they make factually accurate content easier for AI systems to extract and verify — not because of the markup itself (Google Search Central, per DOCTRINE.md).
