---
name: aeo-technical-audit
description: Crawl a target URL and produce an answer-engine-readiness + technical/on-page SEO audit doc for prettyflyforai.com. Propose-only — writes one markdown artifact to the sentinel-drafts inbox. Never touches the live site.
input: optional `url` (defaults to https://prettyflyforai.com), optional `slug` for the output filename
output: /Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-aeo-technical-audit-{slug}.md + Hermes local receipt
---

# Skill: aeo-technical-audit

## Purpose

Run a source-grounded audit of a target URL across five areas: (1) technical health,
(2) on-page fundamentals, (3) answer-engine readiness, (4) entity/schema completeness,
and (5) measurement readiness. Output is one paste-ready markdown doc Alex reviews
and acts on himself.

AEO is not a separate discipline. It is SEO done with structure optimized for AI
answer surfaces (Google AI Overviews, Perplexity, ChatGPT). The foundations are the
same; the additional layer is answer-first content blocks, question-shaped headings,
accurate JSON-LD, and entity consistency. This audit surfaces gaps in both layers.

This skill is propose-only. It never deploys, publishes, edits the live site, or
opens a repository PR.

## Inputs (must read in this order before running)

1. `DOCTRINE.md` in this profile — canonical decision rules, banned tactics, VERIFY-THEN-DEPLOY gate, and output contract
2. `MEMORY.md` in this profile — known audit gaps already on record (do not re-report closed gaps)
3. `USER.md` in this profile — site positioning, ICP, current PrettyFly angle
4. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts, offer names, proof points
5. `~/Projects/marketing/brand/voice-and-anti-slop.md` — banned vocab, voice constraints

## Procedure

### Step 1 — Resolve the target URL

Use the `url` input if supplied, otherwise default to `https://prettyflyforai.com`.
Derive a slug from the URL hostname + path (e.g. `prettyflyforai-com-homepage`) or
use the `slug` input if supplied.

### Step 2 — Fetch page source (no paid APIs)

Attempt to fetch the target URL in this escalation order:

1. `WebFetch` — static pages, no JS rendering needed
2. `firecrawl_scrape` (Firecrawl MCP) — preferred default; returns AI-extracted
   Markdown, title, description, links, and raw HTML metadata
3. `python3 ~/.claude/scripts/stealth-fetch.py <url>` — fallback when Firecrawl
   returns 403/empty or hits Cloudflare protection

Record which fetch method succeeded. If all three fail, stop and write a
`status: fetch-failed` artifact noting the error; do not proceed with invented data.

### Step 3 — Technical health check

From the fetched HTML/Markdown, evaluate:

- **Crawlability**: Does `robots.txt` allow the primary pages? Is an XML sitemap
  referenced and reachable?
- **SSL**: Is the page served over HTTPS? Any mixed-content indicators?
- **Mobile / viewport**: Is `<meta name="viewport">` present?
- **DOCTYPE**: Is `<!DOCTYPE html>` present?
- **SPA / JS rendering**: Is the page a client-rendered SPA where critical metadata
  (title, meta, schema) would be absent from raw HTML? Flag if critical tags are
  missing from raw HTML but the site appears JS-heavy.
- **Performance signals** (if Firecrawl returns them or a pagespeed endpoint is
  available without credentials): note any obvious issues (autoplay video, unoptimized
  hero image). Do not invent performance scores — only cite observable data.
- **Broken links**: Note any 4xx responses returned during the fetch.

For each finding, assign: `severity` (critical / warning / info), `issue` (one
sentence), and `fix` (one concrete action or "no action needed").

### Step 4 — On-page fundamentals check

From the same fetch, evaluate:

- **`<title>` tag**: Present? Character count (target 50-60). Matches brand
  positioning from `prettyfly-company-truth.md`?
- **Meta description**: Present? Character count (target 140-160). Contains primary
  positioning and a soft CTA?
- **Open Graph tags**: `og:title`, `og:description`, `og:image`, `og:type`,
  `og:url` — each present/absent.
- **Twitter/X card tags**: `twitter:card`, `twitter:title`, `twitter:description`,
  `twitter:image` — each present/absent.
- **H1 tag**: Exactly one H1? Text matches primary positioning?
- **Heading hierarchy**: H2/H3 present? Hierarchy logical (no skipped levels)?
- **Image alt text**: Sample of images — are `alt` attributes present and
  descriptive? Do not audit every image; note pattern from visible sample.
- **Internal links**: Are key conversion pages (e.g. `/works`, offers page,
  contact) reachable from the home page via internal links?
- **Thin content**: Word count estimate (target 400+ words on primary page).
  Note if the page is a thin single-screen SPA with minimal crawlable text.
- **Canonical tag**: Is `<link rel="canonical">` present and pointing to the
  correct URL?

For each finding, assign severity + issue + fix, same schema as Step 3.

### Step 5 — Answer-engine readiness check

Per DOCTRINE.md AEO layer:

- **Organization JSON-LD**: Is there a `{ "@type": "Organization" }` block with
  `name`, `url`, `logo`, and at least one `sameAs` link?
- **Other schema types**: Note any `WebPage`, `Article`, `FAQPage`, `HowTo`,
  `Service`, or `Person` blocks present — or absent when the page content warrants them.
- **Answer-first content blocks**: Does the above-fold copy answer the primary buyer
  question ("What does PrettyFly do for you?") in the first 40-60 words, without
  setup or jargon? Flag if the hook is abstract or internal-facing.
- **Question-shaped headings**: Are any H2/H3 tags written as questions a buyer
  would search ("How does the AI Ops Audit work?")? Flag if all headings are
  label-style ("Services", "About", etc.).
- **Entity consistency**: Does the page use a consistent brand name
  ("PrettyFly" / "PrettyFly.ai" / "prettyflyforai.com")? Note any variations
  that would fragment entity signals.
- **`llms.txt`**: Check if `https://{host}/llms.txt` exists. If absent, note it
  as optional/informational only — per DOCTRINE.md it is a crawler access-control
  file, not a citation signal. Do not flag as a gap unless Alex has decided to
  create one.

For each finding, assign severity + issue + fix.

**Citation sources for AEO claims:**
- Google Search Central AI features: https://developers.google.com/search/docs/appearance/ai-overviews
- arXiv 2603.29979 — content structure and citation behavior
- arXiv 2605.14021 — AI Overview activation measurement

### Step 6 — Entity / sameAs consistency check (surface-level)

Without paid tools, do a surface check:

- Does the page `og:url` match the canonical URL?
- Does the `Organization` schema `sameAs` array reference the known social profiles
  (LinkedIn, GitHub, X, Crunchbase) sourced from `prettyfly-company-truth.md`?
- Flag any brand name variants found in the fetched copy that differ from the
  canonical entity name.

Note: a full cross-platform sameAs audit (checking live directory profiles) is
out of scope for this skill — that belongs to a dedicated `entity-consistency-audit`
skill. Flag missing `sameAs` entries in schema only.

### Step 7 — Measurement readiness check

This is a readiness check only — no paid analytics access required:

- Is **Google Search Console** mentioned or linked anywhere visible? (Informational —
  presence check only.)
- Does the site use a standard analytics snippet (GA4 `gtag.js` or similar) visible
  in the page `<head>`? Note script presence/absence without evaluating configuration.
- Does the site have a **UTM convention or referral attribution pattern** visible in
  any `<a href>` links on the page (e.g. utm_source in tracked links)?
- Flag if no analytics snippet is detected — this blocks measurement of AEO
  citation effectiveness per DOCTRINE.md measurement doctrine.

### Step 8 — Gap triage (impact/effort matrix)

Collate all critical and warning findings from Steps 3-7 into a gap table:

| Gap | Severity | Module | Impact | Effort | Next skill |
|-----|----------|--------|--------|--------|------------|
| ... | critical/warning | technical/onpage/aeo/entity/measurement | high/medium/low | high/medium/low | generate-metadata-schema-pack / aeo-question-cluster-brief / etc. |

Assign `impact` and `effort` using these rules:
- **High impact**: gap directly blocks search/AI crawler indexing OR blocks conversion
  signal attribution
- **Medium impact**: gap reduces citation likelihood or weakens entity signal
- **Low impact**: cosmetic or marginal SEO signal improvement
- **High effort**: requires rewriting page copy or restructuring templates
- **Medium effort**: requires adding/editing a `<head>` tag, JSON-LD block, or image attribute
- **Low effort**: one-line HTML or config change

Order by: critical first, then by highest-impact lowest-effort.

### Step 9 — Write the artifact

Write exactly ONE file to:

`/Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-aeo-technical-audit-{slug}.md`

where `{YYYY-MM-DD}` is today's date and `{slug}` is from Step 1.

Use the frontmatter from DOCTRINE.md § Output contract:

```yaml
---
date: {YYYY-MM-DD}
type: sentinel-draft
status: proposed
project: prettyflyforai-seo-aeo
skill: aeo-technical-audit
agent: sentinel
site: {target URL}
audit_gap: baseline-audit
impact: high
effort: medium
verify_after_deploy: "Re-run this skill after deploying fixes. Validate JSON-LD at https://validator.schema.org. Check Open Graph via https://www.opengraph.xyz. Confirm title/meta in GSC Coverage report within 7 days of deploy."
private_payload_redacted: true
fetch_method: {which method succeeded in Step 2}
---
```

Body structure:

```
# AEO + Technical SEO Audit — {target URL} — {date}

## Summary
2-4 sentences: what was audited, critical gap count, most important next action.
No invented metrics. No ranking promises.

## Technical Health
Table or bulleted findings from Step 3. Format: **Issue** | Severity | Fix.
All findings cite the source (fetched page, robots.txt, HTTP response). "No issue found" is a valid entry.

## On-Page Fundamentals
Table or bulleted findings from Step 4. Same format. Each finding cites the field and observed value (e.g. "`<title>` absent — no tag found in raw HTML").

## Answer-Engine Readiness
Table or bulleted findings from Step 5. AEO claims cite Google Search Central or the arXiv anchors from DOCTRINE.md. Never cite "AI ranking signals" without a published source.

## Entity / sameAs Consistency
Table or bulleted findings from Step 6. Note schema fields only; full cross-platform audit is out of scope.

## Measurement Readiness
Findings from Step 7. Flag analytics-absent state clearly — this blocks AEO effectiveness measurement.

## Gap Triage
The impact/effort table from Step 8. This is the actionable handoff surface.

## Verification Steps (run after Alex deploys fixes)
Numbered list:
1. Validate all JSON-LD blocks at https://validator.schema.org
2. Check title/meta/OG tags at https://www.opengraph.xyz/{URL}
3. Confirm new title and meta show in Google Search Console › URL Inspection within 7 days
4. Set up GA4 AI-referral channel group per DOCTRINE.md measurement doctrine to track AEO attribution going forward
5. Re-run aeo-technical-audit skill after fixes are deployed to close the gap record

## Sources
- Page source fetched via {fetch_method} on {date}
- prettyfly-company-truth.md (brand positioning)
- sentinel/DOCTRINE.md (AEO decision rules and source anchors)
- Google Search Central AI features: https://developers.google.com/search/docs/appearance/ai-overviews
- {any other sources cited inline}
```

Do NOT include raw scraped HTML, full page source, or any content that would
violate `private_payload_redacted: true`.

### Step 10 — Emit the Hermes local receipt

After the file is written, invoke the Hermes-local proposal/receipt emitter with:

```
type=sentinel.draft.proposed
status=pending
surface=cli
cwd_project=marketing
skill_slug=aeo-technical-audit
silo_slug=skills
data.runtime=hermes
data.proposal_status=proposed
data.private_payload_redacted=true
data.artifact_type=aeo-technical-audit
data.impact=high
data.effort=medium
data.readout_path=marketing/_inbox/sentinel-drafts/{filename}
```

Confirm the receipt exists and capture the receipt ID into the artifact's footer as
`receipt_id: {uuid}`.

## Validation checklist

Before marking this skill complete, verify each item:

- [ ] Artifact file exists at the exact path in Step 9 — no temp files, no chat
      paste-only output
- [ ] YAML frontmatter is complete with all required fields from DOCTRINE.md §
      Output contract
- [ ] Every finding in the body cites an observable source (fetched field,
      HTTP response, vault file) — no invented metrics
- [ ] AEO claims (citation likelihood, schema behavior) cite Google Search
      Central or an arXiv anchor — not speculation
- [ ] Gap triage table is present and ordered by severity then impact/effort
- [ ] Verification steps section is present with at least the 4 standard checks
- [ ] `llms.txt` was not flagged as a required gap (it is optional per DOCTRINE.md)
- [ ] No banned tactics were proposed (keyword stuffing in JSON-LD, ranking
      promises, magic schema claims, autonomous site edits)
- [ ] Hermes local receipt was emitted and `receipt_id` captured in the artifact
- [ ] No writes occurred outside `_inbox/sentinel-drafts/`

## No-external-side-effects gate

This skill is complete only if ALL of the following are true:

1. The live site was NOT modified, deployed to, or opened via any write tool
2. No repository PR was opened
3. No file was written outside `/Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/`
4. No paid SEO API (DataForSEO, BrightLocal, Semrush, Ahrefs) was called
5. Fetch used only WebFetch, Firecrawl MCP, or stealth-fetch.py (no credentials required)
6. The Hermes receipt does NOT contain raw page source, full HTML, or scraped private content

If any gate fails, do not emit the receipt and do not mark the task complete.
Report the violation and stop.
