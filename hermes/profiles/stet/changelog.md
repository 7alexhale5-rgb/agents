# changelog — stet

## 2026-05-20 — Scaffold from Atlas template (Phase 3 of $1M plan)

Initial profile. Built per the 11-file contract ADR + Hermes ↔ PFOS event
contract ADR + sub-project trigger ADR (Phase 3 of `~/.claude/plans/here-is-what-we-joyful-torvalds.md`
supersedes the 30-day trigger because Stet sits inside the same revenue
motion as Marin + Quill).

- Identity: SOUL / DOCTRINE / USER / MEMORY written against marketing vault
  (voice-and-anti-slop, copy-review-checklist applied adversarially,
  kill-list as KILL trigger, tool-adoption-trigger rule, do-not-scale rule,
  market thesis as drift anchor, message-outcome-ledger for invented-evidence
  detection)
- Router: CLAUDE.md with 5-task routing (critique-draft, critique-campaign-
  brief, critique-positioning, pressure-test-campaign, generate-handoff) +
  3-tier model routing + 11 hard rules
- Config: 4 separate critique tools (one per skill) so per-skill attribution
  in PFOS is correct — `critique_draft.propose`, `critique_campaign.propose`,
  `critique_positioning.propose`, `pressure_test.propose` — each with its own
  event block per the patch #5 emitter contract
- Skills: 5 flat MD (README, critique-draft, critique-campaign-brief,
  critique-positioning, pressure-test-campaign)
- Eval: promptfoo.yaml with anthropic provider direct (no exec proxy);
  6 tests
- Acceptance gate: ONE measurable — first real critique + matching
  agent_events row, falsifiable in 1 SQL query

Lint: PASS (soft mode).
Skills tested: scaffold-level (real eval runs after first invocation).
