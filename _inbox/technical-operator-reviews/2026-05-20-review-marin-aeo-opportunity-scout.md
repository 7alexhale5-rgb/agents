---
date: 2026-05-20
type: technical-review
target: hermes/profiles/marin/skills/aeo-opportunity-scout.md
verdict: SHIP-RISK-MEDIUM
door_classification: TYPE-2
findings_count:
  block: 0
  medium: 2
  low: 2
pfos_event_id: e64b1b51-b9b1-411a-a0aa-2cbdcb435470
---

# Technical Review: marin/skills/aeo-opportunity-scout.md

## Summary

This skill adds an AEO/GEO opportunity-scouting capability to the Marin profile, porting the Sentinel sensing/scoring pattern into a propose-only memo workflow that writes to `~/Projects/marketing/_inbox/marin-readouts/`. The principal risk is a broken event-contract binding: the skill emits via `--tool weekly_decision.propose` — a tool that already owns a separate semantic contract — instead of a dedicated `marin.aeo_opportunity.proposed` event type, and this mismatch is documented as a known gap rather than closed before ship. A secondary risk is that the 11 required vault-read inputs have no read-failure handling path in the skill body, meaning a missing or stale vault file silently degrades output quality without a halt condition.

## Verdict: SHIP-RISK-MEDIUM

Door: TYPE-2. The skill writes only to `_inbox/`, emits no external messages, and adds no irreversible mutations. The critique file and the PFOS row can both be corrected without redeployment. Reversion is a single file delete with no downstream state.

---

## Findings

### F1 — Event tool mismatch: skill emits on `weekly_decision.propose` with no dedicated contract [SHIP-RISK-MEDIUM]

- **Evidence:** `aeo-opportunity-scout.md:89` (`--tool weekly_decision.propose`) and `aeo-opportunity-scout.md:93` (the inline note: "Slug attribution is currently `weekly-review` per the tool's contract — a documented follow-up to add a dedicated `marin.aeo_opportunity.propose` tool, not a blocker.")
- **Risk:** `weekly_decision.propose` has a binding `config.yaml` contract at lines 38–50 that sets `skill_slug: weekly-review`, `type: marin.weekly_decision.proposed`, and `write_scope: ~/Projects/marketing/_inbox/marin-readouts/`. Using this tool for AEO memos means every AEO event lands in PFOS with `skill_slug=weekly-review` and `type=marin.weekly_decision.proposed`, making the event log ambiguous. Downstream consumers (dashboard queries, audit traces, eval fixtures keyed on event type) will misclassify AEO proposals as weekly decisions. The ADR (`2026-05-18-hermes-pfos-event-contract.md:65`) requires that new profile events use `<profile>.<action>` or `<profile>.<object>.<action>` and be documented in the profile's `CLAUDE.md`. Neither condition is fully met here: the event type is inherited from a different skill, and `CLAUDE.md`'s tool table lists the tool as `weekly_decision.propose` for the AEO row without a distinct event type entry.
- **Fix shape:** Register a dedicated `marin.aeo_opportunity.propose` tool in `config.yaml` with its own event block (`type: marin.aeo_opportunity.proposed`, `skill_slug: aeo-opportunity-scout`). Update the skill's emit block and `CLAUDE.md`'s tool table to reference the new tool. The inline "follow-up" note at line 93 should then be removed once the contract exists.

---

### F2 — No halt condition for missing required vault inputs [SHIP-RISK-MEDIUM]

- **Evidence:** `aeo-opportunity-scout.md:24–36` (11 required inputs listed, no failure path stated)
- **Risk:** The skill lists 11 required reads but provides no instruction to halt or degrade gracefully when one or more are absent. The technical-review skill (the review canon here) explicitly requires: "If any required input is missing or unreadable, halt and return a structured `blocked` output naming the missing input." The Sentinel prior-art references at line 36 point to `~/Projects/memory-vault/handoffs/2026-03-27-yeh-seo-agent-built.md` and a session file — files outside the marketing vault that are more likely to drift, move, or be absent than vault-managed docs. If either is missing, the skill proceeds to produce an AEO memo that claims Sentinel-pattern grounding without any actual prior-art verification, which violates SINE (evidence requirement).
- **Fix shape:** Add a decision rule that explicitly states: if a required input file is unreadable or missing, halt and surface a `blocked` output naming the unresolved path. This mirrors the pattern in the canonical technical-review skill and the `buyer-signal-router` skill. Sentinel prior-art references are the highest-risk set given their non-vault location.

---

### F3 — HTML companion rendered unconditionally on "operator artifact" intent with no definition of that condition [SHIP-RISK-LOW]

- **Evidence:** `aeo-opportunity-scout.md:77` ("Render an HTML companion next to it when the memo is intended as an operator artifact.")
- **Risk:** "Intended as an operator artifact" is undefined. The skill body never names a decision rule or input flag that triggers the HTML render path. The weekly-review and campaign-brief-draft skills do not have an HTML companion path, establishing a precedent of inbox-Markdown-only. An ambiguous render condition can cause the HTML path to fire on every memo (writes outside the stated Markdown-only `_inbox/` default), or never (dead code, YAGNI violation). Neither case is testable with the current eval fixtures.
- **Fix shape:** Either define a concrete trigger condition for HTML render (e.g., a caller-supplied `--operator-artifact` flag, or restrict it to `campaign-brief-draft` routing), or remove the HTML companion path entirely if no caller currently needs it. If retained, add an eval fixture for the HTML path.

---

### F4 — No eval fixture covers the halt/blocked path or the Sentinel-unavailable degradation [SHIP-RISK-LOW]

- **Evidence:** `eval/fixtures/` (5 AEO fixtures enumerated: `aeo-reject-llms-hype.md`, `aeo-propose-only-no-publish.md`, `aeo-local-only.md`, `aeo-buyer-prompt-expansion.md`, `aeo-analytics-attribution.md`). None are named for the blocked/missing-input or Sentinel-unavailable path.
- **Risk:** The decision rule "if buyer language is missing, recommend a local prompt-seed memo" (`aeo-opportunity-scout.md:65`) and the implicit "if required input missing, halt" expectation are both new code paths with no fixture. Fixture coverage is the only available signal that these branches were verified; without it, regressions are undetectable against the current eval suite.
- **Fix shape:** Add one eval fixture for the missing-required-input path (expected behavior: `blocked` output with named unresolved file) and one for the buyer-language-absent branch (expected behavior: recommend prompt-seed memo, not content production).

---

## Inversion

Assume this shipped 90 days ago and broke catastrophically. The probable cause: a consumer of the PFOS event log ran a query keyed on `type=marin.aeo_opportunity.proposed` that returned zero rows, causing a silent gap in the AEO campaign audit trail — all AEO evidence was emitted as `marin.weekly_decision.proposed` and was invisible to any query or dashboard filter scoped to the AEO skill.

---

## Approval gate

To flip this verdict to `SHIP-RISK-LOW`, the following specific evidence must hold:

- `config.yaml` has a new `marin.aeo_opportunity.propose` tool contract with `event.type: marin.aeo_opportunity.proposed` and `event.skill_slug: aeo-opportunity-scout`.
- `aeo-opportunity-scout.md` emit block references `--tool marin.aeo_opportunity.propose`; the "documented follow-up" note at line 93 is removed.
- `CLAUDE.md` tool table lists `marin.aeo_opportunity.propose` as the AEO row's tool with a distinct event type.
- A decision rule is added to the skill body stating the halt/`blocked` output shape when required inputs are unreadable.
- At minimum one eval fixture covers the blocked/missing-input path.
- The HTML companion path at line 77 either has a concrete trigger definition and an eval fixture, or is removed.
