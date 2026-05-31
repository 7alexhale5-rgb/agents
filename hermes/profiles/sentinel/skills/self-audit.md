---
name: self-audit
description: Run Sentinel's standard fleet self-audit — review the gap queue, sample recent sentinel-drafts for source-groundedness and completeness, and write a structured evidence report. Catches profile drift and stale gap states without manual review. PROPOSE-ONLY — writes one audit report to _inbox/sentinel-drafts/, never touches the live site or any repo.
input: none (reads MEMORY.md, recent sentinel-drafts inbox, and canonical DOCTRINE.md sources)
output: markdown to /Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-self-audit-{slug}.md + Hermes local receipt (audit_type=self)
---

# Skill: self-audit

## Purpose

Weekly self-grading for the sentinel profile. Sentinel reads its own gap queue,
samples the last 7 days of draft artifacts, checks source-groundedness and
VERIFY-THEN-DEPLOY compliance, and writes a structured evidence report that Alex
can use to decide which gaps to prioritize next.

The fleet's autonomy-gate watcher reads these reports to determine when Sentinel
can graduate individual skills to higher Karpathy rungs. A failed audit still
emits a receipt — the gate watcher needs to know the audit ran even when findings
are negative.

**Success criterion (falsifiable):** One evidence file lands in
`_inbox/sentinel-drafts/` with `type: sentinel-draft`, `skill: self-audit`,
`status: proposed`, and at least one of the required section headers present.
No external writes, no site changes, no repo PRs.

## Inputs (must read in this order before generating)

1. `MEMORY.md` — current gap queue, boot anchors (title/meta/OG/schema audit state), HIGH-risk gaps, any session notes; this is the primary evidence source for gap freshness
2. `DOCTRINE.md` — the full decision rule set, banned tactics table, measurement doctrine, and output contract; used as the grading rubric
3. `USER.md` — prettyflyforai.com positioning and ICP; used to spot positioning drift in prior artifacts
4. `~/Projects/marketing/brand/prettyfly-company-truth.md` — canonical company facts; used to verify claims in sampled drafts are source-grounded
5. `~/Projects/marketing/brand/voice-and-anti-slop.md` — voice spine and banned vocab; used in the banned-vocab sweep over sampled drafts
6. `~/Projects/marketing/_inbox/sentinel-drafts/` — the last 7 days of draft files; enumerate by filename and read each one
7. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md` — confirm no sampled draft recommended a tool without a trigger

## Procedure

1. **Read all inputs.** Work through the seven inputs above in order. Do not
   skip `MEMORY.md` — it carries the gap queue that drives the audit score. Do
   not skip `DOCTRINE.md` — it is the grading rubric.

2. **Inventory the gap queue.** From `MEMORY.md`, extract the current gap list.
   For each gap record:
   - gap name
   - risk level (HIGH / MEDIUM / LOW as stated in MEMORY.md)
   - whether a `sentinel-draft` file covering this gap exists in the inbox
   - if covered: date of the most recent covering draft, its `status` field, its
     `verify_after_deploy` field (present / absent)
   - if covered: has the gap been marked closed in MEMORY.md (yes / no)

   Emit this as a table under `## Gap Queue Inventory`.

3. **Sample recent drafts.** List every file in
   `~/Projects/marketing/_inbox/sentinel-drafts/` dated within the last 7 days.
   For each file:
   - filename and date
   - `skill` frontmatter field (which skill produced it)
   - `audit_gap` frontmatter field
   - `impact` / `effort` frontmatter fields
   - `verify_after_deploy` frontmatter field (present / absent / value)
   - `private_payload_redacted` field (true / false / missing)
   - Body spot-check: does the body contain a paste-ready code block or
     structured output (yes / no)?
   - Source-groundedness: does every factual claim cite a vault file or
     canonical source anchor from DOCTRINE.md `§ Canonical source anchors`
     (yes / no / partial)?
   - Banned-vocab sweep: any hit of "boost your SEO", "dominate the rankings",
     "10x your traffic", "game-changing", "magic schema", "guarantee", "llms.txt
     will", "AI-powered SEO", or any banned word from
     `voice-and-anti-slop.md` (list hits or "none")?
   - VERIFY-THEN-DEPLOY compliance: does the artifact include a verification
     step for Alex to confirm the change after deploy (yes / no)?

   Emit this as a table under `## Recent Draft Sample`.

4. **Compute audit scores.** Calculate:
   - `gap_coverage_rate` = (gaps with a covering draft) / (total gaps in queue)
     as a percentage
   - `draft_complete_rate` = (drafts that passed all 5 checks: paste-ready body
     + source-grounded + no banned vocab + verify step present +
     private_payload_redacted=true) / (total sampled drafts) as a percentage
   - `stale_gaps` = count of HIGH-risk gaps with no covering draft or last
     covered more than 14 days ago
   - List any drafts that failed one or more checks, with the specific failure
     reason

   Emit as `## Audit Scores`.

5. **AEO practice check.** Review the sampled drafts and gap queue for
   alignment with the four AEO structural requirements from DOCTRINE.md
   `§ AEO = normal SEO + structure`. For each requirement, note whether the
   prior work addressed it or left it open:
   - Answer-first content blocks (40-60 words, direct answer in first sentence)
   - Question-shaped H2/H3 headings matching actual user/AI query forms
   - FAQPage / HowTo / Article + Organization/Person JSON-LD in the artifact
     queue
   - Entity / sameAs consistency across LinkedIn, Crunchbase, GitHub, X

   Note which AEO gaps are still open with no covering draft in the queue.
   Emit as `## AEO Coverage Check`.

6. **Measurement readiness check.** State whether the measurement infrastructure
   DOCTRINE.md `§ Measurement doctrine` specifies is in place, based on what is
   known from MEMORY.md and USER.md:
   - GSC connected (known / unknown / gap)
   - GA4 AI-referral channel group configured (known / unknown / gap)
   - Self-reported AI attribution mechanism in place (known / unknown / gap)

   If any are unknown, flag as an open audit question for Alex — do not invent
   status. Emit as `## Measurement Readiness`.

7. **Recommended next artifacts.** Based on the gap queue inventory and audit
   scores, list the top 3 artifacts Sentinel should produce next, ranked by
   impact/effort from DOCTRINE.md `§ Output contract`. For each:
   - gap name
   - recommended skill slug
   - rationale (one sentence citing the gap source from MEMORY.md)

   If `gap_coverage_rate` is 100% and `stale_gaps` is 0, note that no new
   artifacts are needed and the recommended action is gap queue refresh from
   a live site crawl.

   Emit as `## Recommended Next Artifacts`.

8. **Write the evidence file.** Write one markdown file to:

   `/Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-self-audit-{slug}.md`

   where `{slug}` is `gap-queue-{YYYY-MM-DD}` (e.g.
   `gap-queue-2026-05-30`).

   Frontmatter:
   ```yaml
   ---
   date: {YYYY-MM-DD}
   type: sentinel-draft
   status: proposed
   project: prettyflyforai-seo-aeo
   skill: self-audit
   agent: sentinel
   site: prettyflyforai.com
   audit_gap: self-audit
   audit_type: self
   gap_coverage_rate: {pct}
   draft_complete_rate: {pct}
   stale_gaps: {count}
   impact: low
   effort: low
   verify_after_deploy: "n/a — audit report only, no site change"
   private_payload_redacted: true
   ---
   ```

   Body: the five sections from steps 2-7 above, in order.

9. **Emit the Hermes receipt.** After the file is confirmed written, emit a safe
   `sentinel.draft.proposed` event per the Hermes-local proposal/receipt
   contract:

   ```text
   Write or verify the Hermes local receipt for the inbox artifact. Do not call
   the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
   ```

   Receipt fields: `type=sentinel.draft.proposed`, `status=pending`,
   `surface=cli`, `cwd_project=marketing`, `skill_slug=self-audit`,
   `silo_slug=skills`, `data.runtime=hermes`, `data.audit_type=self`,
   `data.proposal_status=proposed`, `data.private_payload_redacted=true`.
   The receipt may include `gap_coverage_rate`, `draft_complete_rate`,
   `stale_gaps`, and the vault-relative draft path. It must not include raw
   page source, full HTML, or any scraped private content.

## Anti-patterns

- Skipping `MEMORY.md` read because "nothing visibly changed" — the gap queue
  may have been updated by a prior skill or by Alex; always re-read
- Editing or omitting failing checks from the draft sample rather than reporting
  them — the audit value is the accurate failure list, not a clean scorecard
- Reporting `gap_coverage_rate` or `draft_complete_rate` without listing the
  specific gaps or drafts that failed — percentages without evidence are
  not audit output
- Producing the self-audit report as inline chat prose instead of writing the
  evidence file — the file is the deliverable, not the chat reply
- Proposing schema changes, metadata edits, or site modifications in the audit
  report — this skill is diagnostic only; fixes route to the appropriate skill

## Failure modes

- If `MEMORY.md` is missing or has no gap queue entries, note "gap queue empty
  or unreachable" and set `gap_coverage_rate: n/a`. Still write the file and
  emit the receipt with `failure_reason: gap_queue_missing`.
- If `_inbox/sentinel-drafts/` has no files in the last 7 days, set
  `draft_complete_rate: n/a`, note "no recent drafts to sample", and proceed
  with the gap queue inventory and measurement readiness sections only.
- If a vault source from the Inputs list is unreachable, note the file as
  "unavailable" in the relevant section rather than omitting the section.
- In all failure cases, still emit the receipt so the autonomy-gate watcher
  knows the audit ran.

## Validation checklist

Before emitting the Hermes receipt, confirm all of the following are true:

- [ ] All 7 inputs were read (or explicitly noted as unavailable)
- [ ] `## Gap Queue Inventory` table is present with at least one row (or an
      explicit "gap queue empty" note)
- [ ] `## Recent Draft Sample` table is present (or explicit "no recent drafts"
      note)
- [ ] `## Audit Scores` section states `gap_coverage_rate`, `draft_complete_rate`,
      and `stale_gaps` as numbers or "n/a"
- [ ] `## AEO Coverage Check` section addresses all four AEO requirements from
      DOCTRINE.md
- [ ] `## Measurement Readiness` section addresses all three measurement signals
- [ ] `## Recommended Next Artifacts` section lists 1-3 artifacts (or a "no
      new artifacts needed" note)
- [ ] Evidence file was written to the exact path
      `/Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/{YYYY-MM-DD}-self-audit-{slug}.md`
- [ ] Frontmatter has all required fields including `audit_type: self` and
      `verify_after_deploy: "n/a — audit report only, no site change"`
- [ ] `private_payload_redacted: true` is set in frontmatter
- [ ] Hermes receipt was emitted with `audit_type=self` in the data payload

## No external side-effects gate

This skill MUST NOT:

- Write to any file outside
  `/Users/alexhale/Projects/marketing/_inbox/sentinel-drafts/`
- Open a pull request, push a commit, or edit any file in a repo
- Edit, overwrite, or publish any file on prettyflyforai.com or any live site
- Call any tool that sends network traffic to the live site (no auto-crawl)
- Schedule a cron job or recurring monitor
- Recommend a paid SEO tool without a trigger condition in
  `2026-05-16-tool-adoption-triggers.md`

If any of the above is about to occur, stop and flag the violation to Alex
instead of proceeding.
