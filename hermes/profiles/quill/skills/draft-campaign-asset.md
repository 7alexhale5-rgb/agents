---
name: draft-campaign-asset
description: Draft a campaign asset (scorecard section / landing-page copy / offer one-pager) per an active campaign brief. Goes to _inbox/ for Alex review before any promotion.
input: campaign slug + asset type ("scorecard-section" | "landing-copy" | "offer-one-pager") + asset focus
output: markdown to ~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-{asset-type}-{slug}.md + Hermes local receipt
---

# Skill: draft-campaign-asset

## Purpose

Draft ONE campaign asset that Alex can review, edit, and promote into the campaign's active directory. Distinct from `draft-linkedin-field-note` (single post) and `draft-outreach-message` (single DM) — campaign assets are structural pieces of a campaign that get linked and reused.

## Asset types supported

| Type                | Example                                                                                              | Reference shape                                                                                      |
| ------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `scorecard-section` | One section of an AI Operations Scorecard (e.g. "delivery drag", "tool sprawl", "reporting lag")     | `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/scorecard-v0.md` existing section headings |
| `landing-copy`      | One block of landing-page copy (hero / problem / approach / proof / CTA) for an offer or campaign    | `~/Projects/marketing/brand/public-trust-path-activation-2026-05-18.md` for current page state       |
| `offer-one-pager`   | One-page buyer-facing summary of an offer (what it is, who it's for, what you walk away with, price) | `~/Projects/marketing/offers/works-review-buyer-conversion-kit-v0.md` reference for one-pager shape  |

## Inputs (must read in this order)

1. `~/Projects/marketing/brand/voice-and-anti-slop.md`
2. `~/Projects/marketing/brand/prettyfly-company-truth.md`
3. `~/Projects/marketing/brand/copy-review-checklist.md`
4. `~/Projects/marketing/brand/buyer-belief-ladder.md`
5. `~/Projects/marketing/offers/revenue-ladder.md` — the offer being supported lives here
6. `~/Projects/marketing/campaigns/<campaign>/README.md` — campaign goal + state
7. `~/Projects/marketing/campaigns/<campaign>/campaign-brief.md` — campaign brief
8. The relevant existing asset (scorecard / landing copy / offer one-pager) if a revision
9. `MEMORY.md`

## Procedure

1. **Confirm asset type** matches the supported list. If asked for a type not on the list (e.g. "draft a deck", "draft a podcast script"), flag and hold — surface to Alex for scope confirmation.

2. **Confirm the campaign is active.** If the campaign README lists `status: archived` or `paused`, hold and surface.

3. **Identify the buyer belief** this asset moves. Cite the specific rung from `buyer-belief-ladder.md`. One rung per asset.

4. **Identify the offer** the asset supports. Cite the specific entry from `revenue-ladder.md`. One offer per asset.

5. **Draft the asset body** in the format matching its type:
   - `scorecard-section`: heading + 3-5 diagnostic questions + scoring rubric + interpretation guidance + 1-line "what to do next" tied to a measurable
   - `landing-copy`: per-block markdown matching the page's existing block structure (do NOT invent new blocks; match what exists)
   - `offer-one-pager`: header (offer name) + "for whom" (1-2 lines) + "what you get" (bulleted) + "what you walk away with" (1-2 lines) + price + "next step" (single CTA)

6. **Apply the Campaign Copy Gate**: maps to one buyer belief, names one false solution or workflow gap, points toward scorecard/WORKS Review/diagnostic, uses proof language matching evidence level, avoids blending advisory positioning with side lanes.

7. **Apply the 7 sweeps** + banned vocab sweep + Stop Signs check.

8. **Content Rule check**: brand rule + offer + audience + source + measurable next step all linked in frontmatter.

9. **Write** to `~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-{asset-type}-{slug}.md` with frontmatter per `DOCTRINE.md § Output contract`, `type: quill-draft`, `pillar: <1-5>`, `campaign: <campaign-slug>`, `asset_type: <scorecard-section|landing-copy|offer-one-pager>`, all content-rule links filled.

10. **Write Hermes local receipt**:

```text
Write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
```

## Anti-patterns

- Inventing scorecard dimensions not grounded in `content-pillars.md`
- Landing copy that adds new blocks (CTA buttons, social proof carousels) not in the existing page structure
- Offer one-pagers that combine multiple offers ("WORKS Review + Audit + Vision Sprint bundle") — one offer per asset
- Pricing not from `revenue-ladder.md`
- Audience descriptions broader than the campaign's stated ICP
- Anything blending advisory positioning with side lanes (D2C, $500 website, affiliate)

## Failure modes

- Asset type unsupported → hold + surface to Alex
- Campaign archived/paused → hold + surface
- Asset supports a killed item → refuse per kill list, surface
- Offer not on the revenue ladder → hold + ask if revenue ladder needs updating (Alex decides, not Quill)
- Content Rule missing a link → mark `status: incomplete` in frontmatter and surface what's missing
