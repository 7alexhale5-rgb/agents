---
name: critique-positioning
description: Critique a positioning claim against market thesis, buyer belief ladder, and channel positioning map. For new About copy, taglines, offer descriptions before they hit public surfaces.
input: positioning claim (text) + intended surface (e.g. "LinkedIn personal headline", "PrettyFly company page About", "@alexdoesai bio", "offer one-pager hero")
output: markdown to ~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-critique-positioning-{slug}.md + Hermes local receipt
---

# Skill: critique-positioning

## Purpose

Pressure-test a positioning claim BEFORE it goes onto a public surface. Distinct from `critique-draft` (full-asset critique) — this targets a single claim or short copy block at the moment it would change positioning.

## Inputs

1. `SOUL.md`, `DOCTRINE.md`, `MEMORY.md`
2. The positioning claim (provided by Alex or Marin) + intended surface
3. `~/Projects/marketing/brand/market-thesis-v0.md` — the positioning anchor
4. `~/Projects/marketing/brand/buyer-belief-ladder.md` — buyer-journey rungs
5. `~/Projects/marketing/brand/channel-positioning-map-v0.md` — per-channel rules
6. `~/Projects/marketing/brand/prettyfly-company-truth.md` — company facts + category ("AI Liberation")
7. `~/Projects/marketing/brand/voice-and-anti-slop.md` — voice standard + banned vocab
8. `~/Projects/marketing/brand/public-trust-path-activation-2026-05-18.md` — current public-surface state and what each surface owns
9. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md` — positioning items on the kill list

## Procedure

1. **Check kill triggers (verdict = KILL on any hit):**
   - Does the claim embody a kill-list item (E-REP-first positioning, generic AI education framing, workshop-only buildout, deck-only consulting framing, cheapest-AI-vendor positioning)?
   - Does the claim contradict `market-thesis-v0.md` (e.g. pitches "more AI" instead of AI Liberation; positions PrettyFly as a generic AI agency or deck-only shop or cheapest-vendor)?

2. **Sweep the claim itself:**
   - **Voice** (per `voice-and-anti-slop.md`): banned vocab hits? Generic consultant phrasing? AI thought-leader tells?
   - **Specificity** (per `copy-review-checklist.md`): could this claim apply to any AI agency? Or does it name the AI Liberation category, the implementation-heavy service firm audience, the audit-first motion?
   - **Proof** (per `voice-and-anti-slop.md § Content Rule`): does the claim need evidence the vault doesn't have?
   - **Audience fit** (per `prettyfly-company-truth.md § First 30-Day Audience`): does the claim resonate with implementation-heavy service firms, or does it drift to enterprise / pre-revenue / cheapest-vendor audiences?

3. **Buyer belief alignment** (per `buyer-belief-ladder.md`): which rung does the claim move? If it skips rungs (e.g. "buy the audit" before "PrettyFly understands my workflow drag"), that's a `warn` finding.

4. **Channel fit** (per `channel-positioning-map-v0.md`): does the claim match the rules for its intended surface? LinkedIn personal headline rules differ from PrettyFly company page About rules differ from `@alexdoesai` bio rules. Mismatch = `warn` finding.

5. **Public-surface state** (per `public-trust-path-activation-2026-05-18.md`): does the surface require Alex's field-by-field approval before saving (LinkedIn personal headline / About / experience / services; PrettyFly company tagline / About; `@alexdoesai` bio)? If yes, that approval is implied even on a SHIP verdict — flag in body.

6. **Decide verdict.** Kill trigger → `KILL`. 1+ critical or 3+ warn → `REVISE`. Otherwise `SHIP`.

7. **Write critique** to `~/Projects/marketing/_inbox/stet-critiques/{YYYY-MM-DD}-critique-positioning-{slug}.md`. `target_artifact_type: positioning-claim`. Body MUST include the quoted claim, the intended surface, and the channel-fit + buyer-belief alignment finding for that specific surface.

8. **Write Hermes local receipt**:

```text
Write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
```

## Anti-patterns

- Pure stylistic edits ("this could be punchier") — that's not a critique, that's preference
- Critiquing positioning without referencing the specific public surface it's headed to
- Missing the buyer-belief-rung mapping
- Forgetting that public-surface-approval-required claims need Alex's go even on SHIP

## Failure modes

- Claim doesn't have a target surface → cannot run channel-fit check; flag with `info` finding requesting surface
- Surface isn't in `channel-positioning-map-v0.md` → flag with `warn` finding requesting Marin to add it before any positioning change ships there
- Claim is too vague to position against (e.g. "we should sound more confident") → return with `info` finding asking for the specific claim text
