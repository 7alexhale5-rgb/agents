---
name: kill-list-enforce
description: When a request would touch a killed item or adopt a tool without a trigger, produce a 5-line memo declining or proposing-with-evidence.
input: a marketing request, idea, or proposal
output: 5-line memo (inline response or written to ~/Projects/marketing/_inbox/cmo-readouts/{YYYY-MM-DD}-kill-check-{slug}.md if long)
---

# Skill: kill-list-enforce

## Purpose

When Alex asks "should we do X?" or a campaign idea surfaces that would touch a killed item, surface the kill-list violation cleanly and propose the path that respects the doctrine.

## Inputs (must read before responding)

1. `~/Projects/marketing/decisions/2026-05-16-marketing-engine-kill-list.md`
2. `~/Projects/marketing/decisions/2026-05-16-tool-adoption-triggers.md`
3. `~/Projects/marketing/agents/cmo-operating-brief.md` (Kill List section)
4. `~/Projects/marketing/offers/revenue-ladder.md` (to check ladder integrity)

## Killed items (current list — re-check the file)

- Generic AI education content
- E-REP-first positioning
- Workshop-only buildout
- Affiliate-first monetization
- D2C/TikTok Shop as main lane
- $500 website offer on premium channels
- Unpriced "pick my brain" calls
- Tool adoption without trigger
- Content without CTA

## Procedure

1. Identify which killed item (if any) the request touches
2. Cite the kill rationale from the decision doc
3. Cite the reopen rule (metric proves demand AND bottleneck requires it AND ladder stays clear AND CMO brief updated)
4. Decide:
   - **DECLINE** — the request is squarely in the kill list and no reopen criteria fire
   - **PROPOSE WITH EVIDENCE** — the request is adjacent to a killed item but has a real signal; produce a memo with the citation and recommend Alex consider a written decision doc
   - **GREEN-LIGHT** — the request looks like a killed item but is actually outside (e.g. a Field Note that has a CTA is NOT "content without CTA")

## Output shape (5 lines)

```
Claim: <what was being proposed>
Killed item touched: <name from the list>
Kill rationale: <one-line from the decision doc>
Reopen criteria: <all four must fire — list which are/are-not met>
Recommendation: <DECLINE | PROPOSE WITH EVIDENCE (drafting a decision doc) | GREEN-LIGHT (this is actually outside the kill list because <reason>)>
```

## When the answer is "no" be specific

Don't say "this violates the kill list." Say which item, which rationale, and what evidence would unlock the reopen criteria. The goal is to make the right next move obvious, not to be a gatekeeper.

## Tool-adoption-trigger variant

If the request is about adopting a new marketing tool (CRM, automation platform, sequencer, paid ads tool, etc.):

1. Check `decisions/2026-05-16-tool-adoption-triggers.md` for the trigger condition for that tool category
2. If no trigger has fired, produce a memo: `Tool: <name>. Trigger required: <condition>. Trigger status: not fired. Recommendation: defer until <condition>.`
3. If trigger has fired, produce a memo: `Tool: <name>. Trigger condition met: <evidence>. Recommendation: proceed with adoption + write decision doc capturing the trigger evidence.`
