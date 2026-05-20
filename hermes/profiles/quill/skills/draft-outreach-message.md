---
name: draft-outreach-message
description: Draft a post-acceptance workflow-question DM for the AI Ops Audit campaign. Never cold outreach. Only the campaign-authorized next-move format.
input: target prospect (handle + 1-3 lines of public signal) + acceptance context
output: markdown to ~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-dm-{prospect-slug}.md + paired quill.draft.proposed PFOS event
---

# Skill: draft-outreach-message

## Purpose

Draft ONE post-acceptance workflow-question DM that Alex can review and manually send via LinkedIn after a connection request has been accepted. This is the CURRENT campaign-authorized next move per `~/Projects/marketing/outreach/first-response-operating-packet-2026-05-17.md`. No other outbound formats are authorized right now.

## Hard scope rules

- **NEVER draft cold outreach.** The campaign authorizes only manual connection notes (Alex writes those) and post-acceptance DMs. Refuse politely if asked.
- **NEVER draft for a prospect outside the AI Ops Audit selected list** (CSpring, Flexware Innovation, Moser Consulting, Onebridge, SEP, DeveloperTown, Element Three, GadellNet, Resultant, enVista). Held: Kinney Group, Aunalytics, netlogx, Resmed. If asked for a non-listed prospect, flag and hold.
- **NEVER include a calendar link in a first DM.** The buyer hasn't earned that ask. The CTA is a workflow question.

## Inputs (must read in this order)

1. `~/Projects/marketing/brand/voice-and-anti-slop.md`
2. `~/Projects/marketing/brand/copy-review-checklist.md`
3. `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/README.md`
4. `~/Projects/marketing/campaigns/prettyfly-ai-ops-audit-v0/outreach-message-set.md` — existing approved message language
5. `~/Projects/marketing/outreach/first-response-operating-packet-2026-05-17.md` — the active operating packet for current live notes
6. `~/Projects/marketing/outreach/reply-handling.md` — buyer-signal routing rules
7. The target prospect's public signal (provided by Alex — LinkedIn About, recent post, company About page, job posting)
8. `MEMORY.md`

## Procedure

1. **Confirm the prospect is on the selected list** (10 names above). If not, write nothing — return "prospect not on AI Ops Audit selected list; hold" and exit.

2. **Identify ONE public signal** the buyer has shared (recent post, company hire announcement, tool migration, growth milestone, hiring page). Quote or paraphrase one specific line. No invented signals.

3. **Frame ONE bounded inference.** "Saw your team is hiring 3 implementation consultants — looks like the delivery org is scaling fast." Bounded means: based on the public signal, not extrapolated to private pain.

4. **Ask ONE workflow question.** Examples: "When the new IC's onboard, how do they currently learn your delivery playbooks?" / "How are you tracking handoff quality between solutions and implementation?" / "Where does the proposal-to-kickoff handoff currently slow down?" The question earns a workflow naming, not a meeting.

5. **No fake compliment.** No "love what you're building" / "huge fan of your work". The public signal IS the implicit acknowledgement.

6. **No generic AI pitch.** No "we help teams use AI". The DM is a workflow question, not a pitch.

7. **No claim PrettyFly knows private pain.** Bounded inference only. "Looks like" not "I know your team is struggling with".

8. **No pressure for a meeting.** No calendar link, no "want to chat?", no "got 15 minutes?". The CTA IS the workflow question.

9. **Length check**: 3-5 sentences, ~60-90 words. LinkedIn DMs that exceed that get skimmed past.

10. **Apply Outbound Note Gate** (verbatim from copy-review-checklist):
    - one public signal ✓
    - one bounded inference ✓
    - one workflow question ✓
    - no fake compliment ✓
    - no generic AI pitch ✓
    - no claim PrettyFly knows private pain ✓
    - no pressure for a meeting ✓

11. **Apply the 7 sweeps** (Clarity / Voice / So-what / Proof / Specificity / CTA / Compliance). Every sweep passes.

12. **Banned vocab sweep**: same as Field Note skill.

13. **Write** to `~/Projects/marketing/_inbox/quill-drafts/{YYYY-MM-DD}-dm-{prospect-slug}.md` with frontmatter per `DOCTRINE.md § Output contract`, `type: quill-draft`, `pillar: outreach`, `campaign: prettyfly-ai-ops-audit-v0`, `content_rule_links` filled. Include the public signal source (URL or vault path) in the frontmatter.

14. **Emit PFOS event**:

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile quill \
  --tool draft_outreach.propose \
  --readout-path "_inbox/quill-drafts/<YYYY-MM-DD>-dm-<prospect-slug>.md" \
  --extra-json '{"pillar":"outreach","campaign":"prettyfly-ai-ops-audit-v0","prospect":"<slug>","content_rule_complete":true}'
```

## Output shape (body)

```
Hi [Name] —

[ONE public signal, quoted or paraphrased]. [ONE bounded inference about the workflow implication, ~1-2 lines].

[ONE workflow question, specific to the inferred workflow, that invites a naming, not a meeting].

[Signature: Alex / PrettyFly]
```

That's it. No PS. No "happy to share more". No calendar link.

## Anti-patterns

- "Hope you're well" / "Hope this finds you well" — generic opener
- "I've been following your work" — fake compliment
- "Quick question" — pressuring framing
- "Got 15 minutes?" / "Open to a chat?" — meeting pressure
- "We help [companies like yours] do [generic outcome]" — AI-pitch in disguise
- Calendar links of any kind
- "Just wondering" / "If you have a sec" — softener-as-filler
- Anything past 5 sentences

## Failure modes

- Prospect not on selected list → hold + return
- No public signal provided → hold + ask Alex for one
- Public signal is "they exist" / "they hire" without specificity → hold + ask for a sharper signal
- Workflow question is generic ("how do you handle ops?") → rewrite to name the specific workflow
- Length exceeds 5 sentences → cut, don't bargain
