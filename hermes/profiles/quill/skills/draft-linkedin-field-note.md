---
name: draft-linkedin-field-note
description: Produce one LinkedIn Field Note draft for the WORKS Review public signal sprint. Manual post from Alex's personal LinkedIn — no scheduling, no automation. Quill's first live skill.
input: optional `topic` (defaults to "WORKS Review applied to a real workflow drag scenario")
output: markdown to ~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-field-note-{slug}.md + Hermes local receipt
---

# Skill: draft-linkedin-field-note

## Purpose

Draft ONE LinkedIn Field Note that Alex can review, edit, and manually post from his personal LinkedIn during the WORKS Review public signal sprint. Field Notes are the active 7-day public content eval per `~/Projects/marketing/content/works-review-public-signal-sprint-v0.md`.

Success metric per the sprint: qualified `2` and `3` signals (named workflow questions from real operators), NOT impressions or likes.

## Inputs (must read in this order before generating)

1. `~/Projects/marketing/brand/voice-and-anti-slop.md` — the voice spine + banned vocab
2. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts, working values, first revenue loop
3. `~/Projects/marketing/brand/copy-review-checklist.md` — the 7 sweeps
4. `~/Projects/marketing/content/content-pillars.md` — pick ONE pillar
5. `~/Projects/marketing/content/works-review-public-signal-sprint-v0.md` — the active sprint context
6. `~/Projects/marketing/brand/buyer-belief-ladder.md` — what the buyer must believe at this rung
7. `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/README.md` — current campaign state
8. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md` — items NOT to propose
9. `MEMORY.md` — pillar definitions + active campaign state

## Procedure

1. **Pick a pillar.** Choose ONE of the 5 content pillars from `content-pillars.md`. Default for sprint: Pillar 1 (Workflow Drag) or Pillar 2 (AI Operations Audits) — both map cleanly to WORKS Review.

2. **Pick a workflow.** Name ONE specific workflow drag scenario — manual handoff, spreadsheet glue, duplicate SaaS, reporting lag, context switching, or knowledge-work bottleneck. Specificity is the test (per copy-review-checklist Specificity sweep).

3. **Map to buyer belief.** Per `buyer-belief-ladder.md`, identify which rung this post moves the reader toward. The post does ONE rung of belief work, not all of them.

4. **Draft the post** in this shape:
   - **Hook (1-2 lines)**: name the workflow drag plainly. No clickbait, no "Most teams don't realize…", no "I used to think X until Y".
   - **Field observation (3-6 lines)**: what you actually see in implementation-heavy service firms. Cite a specific tool class, role, or handoff. Use plain English. No hype.
   - **WORKS Review angle (2-4 lines)**: how a WORKS Review surfaces this kind of drag. Name what gets measured, what gets decided. Don't sell the audit — show the lens.
   - **CTA (1 line)**: ONE low-friction question that earns a workflow comment. Not "DM me". Not "book a call". Default: "If you've seen this in your shop, name the workflow — I'm collecting patterns for the next WORKS Review batch."

5. **Run the 7 sweeps** from `copy-review-checklist.md`. Every sweep must pass. If any sweep fails, apply the matching rewrite prompt and re-check.

6. **Outbound Note Gate check** (verbatim from vault): one public signal, one bounded inference, one workflow question, no fake compliment, no generic AI pitch, no claim PrettyFly knows private pain, no pressure for a meeting.

7. **Campaign Copy Gate check**: maps to one buyer belief, names one false solution or workflow gap, points toward scorecard/WORKS Review/diagnostic, uses proof language matching the evidence level, avoids blending advisory positioning with side lanes.

8. **Stop Signs check**: hold the draft if it needs an unproven claim, tries to sell before diagnosing, sounds like a mass template, asks too much too early, or assumes automation/paid/CRM/cold email.

9. **Content Rule check**: confirm the draft links one brand rule + one offer + one audience + one source + one measurable next step. Fill the frontmatter `content_rule_links:` accordingly. Missing any link = `incomplete` status; surface what's missing and hold.

10. **Banned vocab sweep**: grep the draft for AI hype words ("leverage", "10x", "moat", "compound", "unlock", "next-level", "game-changing", "AI-powered", "revolutionary", "crushing it"). Any hit = rewrite that line.

11. **Write** to `~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-field-note-{slug}.md` using the frontmatter from `DOCTRINE.md § Output contract` with `type: quill-draft`, `pillar: <1-5>`, `campaign: prettyfly-ai-ops-audit-v0`, all `content_rule_links` filled, `sweeps_passed: [clarity, voice, so_what, proof, specificity, cta, compliance]`.

12. **Write safe Hermes local receipt** by invoking:

```text
Write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
```

Confirm the receipt exists and capture the receipt ID into the draft's footer as `receipt_id: <uuid>`.

## Output shape (body, not frontmatter)

```
[Hook — 1-2 lines, plain]

[Field observation — 3-6 lines, names tool class/role/handoff]

[WORKS Review angle — 2-4 lines, shows the lens, doesn't sell the audit]

[CTA — 1 line, earns a workflow comment]

---
Field Note from the WORKS Review public signal sprint. PrettyFly helps implementation-heavy service firms turn messy operations into working AI systems.
```

Max length: ~150 words body. LinkedIn long-form is allowed but Field Notes stay tight — readers scroll fast.

## Anti-patterns to avoid

- "I've seen X" without a tool class, role, or handoff to anchor X
- "Most teams" / "Most companies" generics — name the segment (implementation-heavy service firms)
- AI-pitch hooks: "AI can finally", "automation that actually works", "in the age of AI"
- Calendar links in first-touch — buyer has not earned that ask
- Multi-question CTAs ("comment if X, DM if Y, follow for Z")
- Cite-free claims: "studies show", "research suggests", "everyone knows"
- Quoting CEOs, founders, or marketing books for decoration
- "What do you think?" — that's not a workflow question

## Source citation rule

Every factual claim in the post body must cite a vault file in the draft's frontmatter (`source` link). No source = no claim. Observed patterns from the campaign's first 25 evidence pass are acceptable sources (`source: campaigns/prettyfly-ai-ops-audit-v0/README.md § First 25 Evidence Pass`).
