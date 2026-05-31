---
name: generate-metadata-schema-pack
description: Produce one paste-ready HTML <head> code block that closes the prettyflyforai.com title/meta/OG/Twitter-card and JSON-LD Organization/FAQPage/HowTo gaps identified in the Polsia audit. Propose-only — output lands in ~/Projects/marketing/_inbox/sentinel-drafts/ for Alex to paste and deploy himself.
input: optional `page_url` (defaults to prettyflyforai.com homepage); optional `faq_questions` list (defaults to 6 canonical buyer questions); optional `howto_process` label (defaults to "WORKS Review onboarding")
output: markdown file at ~/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-generate-metadata-schema-pack-{slug}.md containing one complete code block + verification checklist + Hermes local receipt
---

# Skill: generate-metadata-schema-pack

## Purpose

Close the three HIGH-risk metadata gaps from the Polsia audit of prettyflyforai.com in a single artifact:

1. `<title>` — missing (want 60-char form matching positioning)
2. Meta description — missing (want 155-char form, keyword-bearing, offer-grounded)
3. Open Graph tags — missing (og:title, og:description, og:image, og:type, og:url)

Also produce Twitter card tags and JSON-LD `Organization`, `FAQPage`, and `HowTo` blocks as one complete, paste-ready `<head>` code block. One deliverable, one file, one deploy. **Do NOT deploy, edit the live site, or open a PR. Alex pastes this himself.**

Positioning anchor for all copy: **"Workflow-First AI Operations & Systems Advisory for service businesses."** (Source: Polsia audit output + `USER.md`.)

## Inputs (must read in this order before generating)

1. `MEMORY.md` (sentinel profile boot anchors) — current audit gap record; confirm the title/meta/OG fields are still missing before proceeding. If any field is already correctly populated, note it and skip that component.
2. `USER.md` (sentinel profile) — prettyflyforai.com site URL, canonical entity name, ICP, and positioning.
3. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts, service description, offer names, and proof points used in copy. Every value in the output (description, FAQPage answers, HowTo steps) must trace here.
4. `~/Projects/marketing/brand/voice-and-anti-slop.md` — voice spine and banned vocab. All copy-bearing fields (meta description, og:description, FAQ answers) must pass the voice check.
5. `/Users/alexhale/Projects/agents/docs/competitive-intel/polsia/03-seo-aeo-social-task-playbook.md` — task #1 (metadata + Organization schema pack) and task #2 (FAQPage + HowTo schema) prompt templates and field specs.
6. `DOCTRINE.md` (sentinel profile) — VERIFY-THEN-DEPLOY gate, banned tactics, and output contract (frontmatter shape).

## Procedure

1. **Verify current site state.** Read `MEMORY.md` audit gap anchors. Confirm which of the following fields are confirmed missing vs. already present on the live homepage: `<title>`, `<meta name="description">`, `og:title`, `og:description`, `og:image`, `og:type`, `og:url`, `twitter:card`, `twitter:title`, `twitter:description`, JSON-LD `Organization`, `FAQPage`, `HowTo`. Log a "gap confirmed / already present" status for each. Skip any field that is already correct.

2. **Draft `<title>`.** Use the Polsia audit target: `PrettyFly.ai — Workflow-First AI Operations & Systems Advisory`. Confirm char count ≤ 60. Source: `[POLSIA-AUDIT]`, `USER.md`.

3. **Draft meta description.** Use the Polsia audit target as the starting point: `AI operations advisory + systems execution for service businesses. Workflow-first approach to eliminate operational drag. WORKS Review included.` Confirm char count ≤ 155. Cross-check every noun and offer name against `prettyfly-company-truth.md`. If any claim is not grounded there, rewrite with a claim that is. Source: `[POLSIA-AUDIT]`, `prettyfly-company-truth.md`.

4. **Draft Open Graph block.** Fields required:
   - `og:type` = `website`
   - `og:url` = canonical homepage URL from `USER.md`
   - `og:title` = same as `<title>` unless a shorter form is warranted (≤ 60 chars)
   - `og:description` = same as meta description (≤ 155 chars)
   - `og:image` = use the site's primary OG image URL if known from `USER.md` or `MEMORY.md`; if unknown, insert a clear placeholder comment `<!-- REPLACE: /path/to/og-image.png (1200×630) -->`
   Source: Polsia task #1 prompt spec, `USER.md`.

5. **Draft Twitter card block.** Fields required:
   - `twitter:card` = `summary_large_image`
   - `twitter:title` = same as `og:title`
   - `twitter:description` = same as meta description
   - `twitter:image` = same as `og:image` (or placeholder)
   Source: Polsia task #1 prompt spec.

6. **Draft JSON-LD `Organization` schema.** Required fields: `@context`, `@type`, `name`, `url`, `logo`, `description`, `sameAs` array. For `sameAs`, include LinkedIn, X (Twitter), GitHub, and any Crunchbase URL listed in `USER.md` or `prettyfly-company-truth.md`. If a URL is unknown, insert a comment placeholder rather than inventing a value. All field values must be factually accurate and traceable to `prettyfly-company-truth.md` or `USER.md` — no invented facts. Source: Polsia task #1 prompt, Google Search Central structured data docs, `prettyfly-company-truth.md`.

7. **Draft JSON-LD `FAQPage` schema.** Use 6 buyer questions grounded in actual buyer language. If `faq_questions` input was provided, use those; otherwise derive from `prettyfly-company-truth.md` offer descriptions and ICP pain points. Each answer: 40-60 words, answer-first (first sentence answers the question directly), traceable to company truth. Do NOT invent answers. Pass each answer through the voice check (banned vocab from `voice-and-anti-slop.md`). Source: Polsia task #2 prompt, `prettyfly-company-truth.md`.

8. **Draft JSON-LD `HowTo` schema.** Model the engagement/onboarding process. If `howto_process` input was provided, use that label; otherwise use "WORKS Review onboarding". Steps must match the actual process described in `prettyfly-company-truth.md`. Required fields: `@type`, `name`, `description`, `step` array (each step: `@type: HowToStep`, `name`, `text`). Source: Polsia task #2 prompt, `prettyfly-company-truth.md`.

9. **Assemble the complete code block.** Combine all components — `<title>`, meta description, OG tags, Twitter card, JSON-LD Organization/FAQPage/HowTo — into ONE `<head>` code block in HTML. Order: `<title>` → `<meta name="description">` → OG block → Twitter card block → JSON-LD scripts. Wrap in a single fenced code block (` ```html `). No prose inside the code block.

10. **Run the banned-tactics gate.** Confirm the output contains none of the following (per `DOCTRINE.md § Banned tactics`): llms.txt references presented as primary AEO tactic, ranking promises, "magic schema" language, autonomous-deploy instructions. If any is found, rewrite or remove.

11. **Run the voice gate.** Confirm all copy-bearing fields (meta description, og:description, FAQ answers, HowTo description) pass the banned-vocab check from `voice-and-anti-slop.md`. Any hit = rewrite that field.

12. **Run the source-grounding gate.** Confirm every factual claim in the output (company name, offer names, process steps, sameAs URLs) is traceable to `prettyfly-company-truth.md` or `USER.md`. Any unverified claim = replace with a comment placeholder `<!-- VERIFY: <description of needed info> -->` rather than inventing a value.

13. **Compose the deploy instruction line.** Add a clearly visible section immediately above the code block:

    > **DO NOT DEPLOY — Alex pastes this himself.** Copy the code block below and paste it into the site's `<head>` element (before the closing `</head>` tag). Remove any existing title, meta description, OG, or JSON-LD blocks that this replaces. Then run the verification checklist below.

14. **Compose the validation checklist.** After the code block, add:
    - [ ] `<title>` visible in browser tab and Google Search Console preview
    - [ ] Meta description visible via `curl -s https://prettyflyforai.com | grep -i "meta name=\"description\""` or view-source
    - [ ] OG tags verified at https://developers.facebook.com/tools/debug/ (Facebook Sharing Debugger) — enter site URL, confirm og:title, og:description, og:image render correctly
    - [ ] Twitter card verified at https://cards-dev.twitter.com/validator (or X Card Validator) — confirm `summary_large_image` renders
    - [ ] JSON-LD validated at https://validator.schema.org/ — paste each JSON-LD block; confirm zero errors, zero warnings for required fields
    - [ ] Google Rich Results Test at https://search.google.com/test/rich-results — confirm Organization, FAQPage, HowTo recognized
    - [ ] No console errors on live page after paste (open DevTools → Console → reload)

15. **Write the artifact.** Write to:

    `/Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-generate-metadata-schema-pack-{slug}.md`

    where `{slug}` is `homepage` for the site homepage (or a URL-derived slug for other pages). Use the frontmatter from `DOCTRINE.md § Output contract`:

    ```yaml
    ---
    date: {YYYY-MM-DD}
    type: sentinel-draft
    status: proposed
    project: prettyflyforai-seo-aeo
    skill: generate-metadata-schema-pack
    agent: sentinel
    site: prettyflyforai.com
    audit_gap: title-meta-og-missing
    impact: high
    effort: low
    verify_after_deploy: "validate JSON-LD at validator.schema.org; check OG at Facebook Sharing Debugger; confirm title/meta in GSC"
    private_payload_redacted: true
    ---
    ```

16. **Emit Hermes local receipt.** After the file is confirmed written, emit a `sentinel.draft.proposed` receipt per the Hermes-local proposal/receipt contract: `type=sentinel.draft.proposed`, `status=pending`, `surface=cli`, `cwd_project=marketing`, `skill_slug=generate-metadata-schema-pack`, `silo_slug=skills`, `data.runtime=hermes`, `data.proposal_status=proposed`, `data.private_payload_redacted=true`. The receipt may include: artifact type (`metadata-schema-pack`), impact (`high`), effort (`low`), gap name (`title-meta-og-missing`), confidence level, source file names, and the vault-relative draft path. It must NOT include the full HTML code block, raw page source, or any scraped private content.

## Validation gate

Before the artifact is considered complete, all of the following must hold. If any fails, fix and re-check before writing the file.

| Gate | Check | Pass condition |
| --- | --- | --- |
| Gap confirmed | `MEMORY.md` or live site check shows fields still missing | At least one confirmed gap; any already-correct field skipped |
| Title length | `len(<title> value)` | ≤ 60 characters |
| Meta description length | `len(meta description value)` | ≤ 155 characters |
| Source grounding | Every factual claim traceable | No invented metrics, URLs, offers, or company facts |
| Voice compliance | No banned vocab | Zero hits from `voice-and-anti-slop.md` banned list |
| Banned tactics | No llms.txt as AEO, no ranking promises, no magic-schema | Zero hits from `DOCTRINE.md § Banned tactics` |
| Code block completeness | All 5 component groups present | `<title>`, meta desc, OG block, Twitter card, JSON-LD (Organization + FAQPage + HowTo) in one fenced block |
| Deploy instruction | Visible above code block | "DO NOT DEPLOY — Alex pastes this himself." present |
| Verification checklist | 7-item checklist present after code block | All items from Step 14 present |
| Frontmatter complete | All required DOCTRINE fields present | No missing keys; `status: proposed` |
| No external side-effects | Sentinel has not written to the live site, any repo, or any file outside `_inbox/sentinel-drafts/` | Confirmed: only one file written, to the inbox path above |

**No external side-effects gate (hard stop):** Sentinel is a propose-only agent. This skill must not: edit any file on the live site, push to any git remote, open a pull request, run a deploy command, post to any URL, or modify any file outside `~/Projects/marketing/_inbox/sentinel-drafts/`. If the execution environment offers a deploy path, do not use it. Stop, write the artifact, emit the receipt, and return.
