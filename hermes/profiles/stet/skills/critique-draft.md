---
name: critique-draft
description: Critique one Quill draft. Apply the 7 copy-review sweeps adversarially, cite vault sources for every finding, end with verdict SHIP/REVISE/KILL. Stet's first live skill.
input: target draft path under `~/Projects/marketing/_inbox/quill-drafts/<file>.md`
output: markdown to ~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-critique-{slug}.md + paired stet.critique.proposed PFOS event
---

# Skill: critique-draft

## Purpose

Read one Quill draft, apply the 7 copy-review sweeps adversarially, cite vault sources for every flagged finding, end with a verdict (`SHIP` / `REVISE` / `KILL`). The critique drives either Alex's publish decision (SHIP), Quill's `revise-from-critique` skill (REVISE), or Alex's kill / reopen decision (KILL).

## Hard scope rules

- **Read-only on the draft.** Never modify the file at `_inbox/quill-drafts/<target>`. Only read.
- **Cite a vault file for every flagged finding.** No bare opinions. If no vault standard exists for a test, say so explicitly ("no vault standard yet for X — flagging for Alex to set one") and produce an `info` finding rather than improvising.
- **No rewrite generation.** Name the fix shape ("rewrite the hook in one plain sentence that names the workflow being audited"). Do not write the new hook.

## Inputs (must read in this order)

1. `SOUL.md`, `DOCTRINE.md`, `MEMORY.md`
2. Target draft at `~/Projects/marketing/_inbox/quill-drafts/<file>.md` (full read — frontmatter + body)
3. `~/Projects/marketing/brand/voice-and-anti-slop.md` — voice standard + banned vocab
4. `~/Projects/marketing/brand/copy-review-checklist.md` — the 7 sweeps + Outbound Note Gate + Campaign Copy Gate + Stop Signs
5. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts the draft must align with
6. `~/Projects/marketing/brand/buyer-belief-ladder.md` — what the buyer must believe at the targeted rung
7. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md` — KILL triggers
8. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md` — KILL trigger for unauthorized tool use
9. The draft's own `content_rule_links.source` file (cited in the draft frontmatter) — to verify the source actually says what the draft claims

## Procedure

1. **Read the draft fully.** Parse frontmatter (type, pillar, campaign, content_rule_links, sweeps_passed claimed). Parse body.

2. **Check kill triggers first.** If ANY kill trigger fires, verdict is `KILL` and you skip the rest of the sweeps (the verdict is decided; further findings would be noise):
   - Does the draft propose any item from the kill list (generic AI education, E-REP-first positioning, workshop-only buildout, affiliate-first monetization, D2C/TikTok as main lane, $500 website on premium channels, unpriced "pick my brain" calls, tool adoption without trigger, content without CTA)?
   - Does the draft assume a tool whose adoption trigger has not fired?
   - Does the draft cite invented evidence (a metric / customer name / reply count / conversion number / buyer language NOT in `message-outcome-ledger-v0.md` or any vault source)?

3. **Run the 7 sweeps adversarially.** For each sweep, find where the draft FAILS:
   - **Clarity**: line numbers / quoted phrases where a busy operator gets lost. Cite `copy-review-checklist.md § Clarity`.
   - **Voice**: phrases that sound like a generic consultant or AI thought-leader. Quote them. Cite `voice-and-anti-slop.md`. Banned vocab hits = `critical`.
   - **So what**: claims that don't explain business consequence. Cite `copy-review-checklist.md § So what`.
   - **Proof**: claims without source. Cite `voice-and-anti-slop.md § Content Rule` (which requires a source link) AND the draft's own frontmatter `content_rule_links.source` — verify the source actually backs the claim.
   - **Specificity**: lines that could apply to any company. Cite `copy-review-checklist.md § Specificity`.
   - **CTA**: multi-ask drafts, calendar links in first-touch, "DM me / book a call" before earned. Cite `copy-review-checklist.md § CTA` + the Outbound Note Gate.
   - **Compliance**: assumed automation, paid, CRM, cold-email, or any motion not in scope per the campaign README. Cite `copy-review-checklist.md § Compliance` + the relevant campaign README.

4. **Content Rule check.** Verify the draft's frontmatter `content_rule_links` actually has all 5 fields populated AND each link points to a real vault file. Missing or fake link = `critical` finding.

5. **Length check.** Per skill type:
   - Field Note: ≤150 words body (per Quill's `draft-linkedin-field-note` skill spec)
   - DM: 3-5 sentences, ~60-90 words (per Quill's `draft-outreach-message`)
   - Campaign asset: matches the existing reference shape (no new blocks introduced)
     Length violation = `warn` finding.

6. **Tally severity counts.** Critical / warn / info totals.

7. **Decide verdict.**
   - `SHIP`: 0 critical, ≤2 warn, all sweeps near-pass.
   - `REVISE`: 1+ critical OR 3+ warn, addressable via revision, no kill triggers hit.
   - `KILL`: any kill trigger hit (from step 2).

8. **Write critique** to `~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-critique-{draft-slug}.md` using the frontmatter + body shape from `DOCTRINE.md § Output contract`. `target_artifact_type: quill-draft`. Every finding has: F# title, severity, sweep (or kill-trigger), evidence (quoted phrase or line), source (vault file path), fix path (or "hard-block — surface").

9. **Emit PFOS event**:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile stet \
  --tool critique_draft.propose \
  --readout-path "_inbox/stet-critiques/<YYYY-MM-DD>-critique-<draft-slug>.md" \
  --extra-json '{"verdict":"<SHIP|REVISE|KILL>","critical":<N>,"warn":<N>,"info":<N>,"kill_triggers_hit":[<list>],"target_artifact_path":"_inbox/quill-drafts/<draft-file>"}'
```

Confirm exit 0 and capture the returned row UUID into the critique's footer.

## Anti-patterns to avoid

- Findings without a vault source citation
- Findings without a fix path or hard-block
- Rewriting Quill's copy in the critique (that's Quill's job via `revise-from-critique`)
- Naming or attacking the author (the draft is Quill's, but Quill isn't the target — the artifact is)
- "Soft" verdicts ("leaning toward revise", "consider revising") — pick one
- Performative skepticism — every finding must trace to a real failure
- Skipping the kill-trigger check (running all sweeps then noticing a kill at the end wastes critique surface)
- Inventing standards the vault doesn't have

## Failure modes

- Target draft missing or unreadable → return error, do not write a placeholder critique
- Vault inputs unreachable → return error, do not improvise standards
- Draft cites a `content_rule_links.source` file that doesn't exist → critical finding (Proof sweep), verdict at minimum REVISE
- Draft cites a source that doesn't back the claim it's making → critical finding (Proof sweep), verdict at minimum REVISE
- Kill trigger hit AND draft frontmatter claims `sweeps_passed: true` → critical finding noting the false self-attestation
