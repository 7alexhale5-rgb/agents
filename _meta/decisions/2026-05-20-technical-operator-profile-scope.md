---
date: 2026-05-20
type: decision
project: agents
tags: [adr, hermes, profiles, technical-operator, scope, rung-1, yagni, sine]
status: accepted
related_adrs:
  - 2026-05-20-reserve-codex-for-tool-use-technical-operator-profile.md
  - 2026-05-18-agent-shape-11-file-contract.md
  - 2026-05-18-hermes-pfos-event-contract.md
  - 2026-05-18-subproject-to-profile-trigger.md
  - 2026-05-20-capability-build-sequence.md
---

# ADR: Scope The `technical-operator` Profile At Rung 1 (Read-Only Engineering Reviewer)

## Decision

Create `hermes/profiles/technical-operator/` as the durable engineering-governance profile reserved by the prior codex-boundary ADR. Lock its starting posture:

| Surface              | Setting                                                                                                                                                                                                                                             |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Rung                 | **1** (read-only)                                                                                                                                                                                                                                   |
| Authority            | read-only on code, repos, plans, PRs; **propose-only** writes to `~/Projects/agents/_inbox/technical-operator-reviews/`                                                                                                                             |
| Channels             | **none** (no Slack, no email, no Telegram). Output is inbox files + paired PFOS events only.                                                                                                                                                        |
| Spend cap            | $0/day — profile has no spend authority. Model API spend rolls up to the global fleet ledger.                                                                                                                                                       |
| Tools                | one builtin: `technical_review.propose`. No deploy, merge, send, MCP write tools, or production mutation tools.                                                                                                                                     |
| Shared skills        | inherits all 20 engineering Agency skills previously parked under `PARKED_CANDIDATES["technical-operator"]` in `scripts/build-agency-shared-skills.py`.                                                                                             |
| Profile-local skills | one: `technical-review`.                                                                                                                                                                                                                            |
| Eval suite           | promptfoo fixture suite in `eval/` (seeded; expansion is a separate slice).                                                                                                                                                                         |
| Acceptance gate      | **one real `technical_operator.review.proposed` row in `public.agent_events`** with `surface='cli'`, `cwd_project='agents'`, `skill_slug='technical-review'`, plus the corresponding critique file present in `_inbox/technical-operator-reviews/`. |
| Promotion path       | rung 2+ requires a separate ADR. No autonomous behavior, no merge/deploy authority, no external sends.                                                                                                                                              |

Event type naming uses the existing fleet convention (`namespace.entity.state`, namespace and entity in lowercase with underscores in the entity portion only): `technical_operator.review.proposed`. The codex-boundary ADR used the hyphenated wording `technical-operator.review.proposed` in prose — that was the human-readable form; the wire format follows existing marin/stet/atlas events.

## Why

Three forces converge on this slice:

1. **Codex-boundary ADR already named the future profile.** The 2026-05-20 ADR closed `hermes/profiles/codex/` as fleet identity and reserved `technical-operator` for engineering governance. This slice executes that reservation.
2. **20 parked engineering skills are sitting idle.** `build-agency-shared-skills.py` already produced their SKILL.md files in `hermes/shared-skills/agency/`. They have no owner profile. Without one, the catalog is dishonest about what is actually wired in.
3. **The 2026-05-20 Marin → Stet pilot proved the fleet now produces artifacts that need engineering review.** Marin v2 hallucinated case studies; Stet caught them. The next-class of failure modes — incorrect routing, broken schemas, misused tool contracts, hidden authority creep — needs an engineering review pass, not a marketing-critique pass.

This is the smallest correct next step. It does not collapse engineering governance into autonomous coding; it does not give the profile any execution surface; it does not pre-build retainer-delivery capacity.

YAGNI / SINE / KISS / SOLID / DRY all hold:

- **YAGNI:** No autonomous coding loop. No merge authority. No "future engineering department" pre-build.
- **SINE:** The profile gets one job — read code and proposed plans, produce a critique with verdict, emit one PFOS row. Promotion only when load justifies it.
- **KISS:** Atlas-derived 11-file contract. One profile-local skill. One PFOS event type. One inbox path.
- **SOLID:** One reason to exist (engineering governance). Does not blur into marketing, sales, retainer-delivery, or operator-controlled Codex tooling.
- **DRY:** Inherits the 20 engineering Agency skills already converted; doesn't duplicate them as profile-local files.

## What This Slice Does

1. Writes the 11-file Atlas contract to `hermes/profiles/technical-operator/`.
2. Moves `PARKED_CANDIDATES["technical-operator"]` skills into `PROFILE_ENABLEMENT["technical-operator"]` in `scripts/build-agency-shared-skills.py`, removing the parked entry.
3. Regenerates the agency catalog so the 20 skills become active under the new profile.
4. Adds one profile-local skill: `skills/technical-review.md`.
5. Creates the `_inbox/technical-operator-reviews/` directory in the agents repo.
6. Validates via `lint-profile.sh` + `validate-agency-skills.py`.
7. Smoke-tests `technical-review` against the marin AEO skill file (a real review surface) via the patched `fleet-invoke.sh` from commit `3078b7d`.

## What This Slice Does NOT Do

- Promote the profile past rung 1.
- Wire Slack, Telegram, email, or any external channel.
- Add deploy, merge, send, schedule, MCP write, or production-mutation tools.
- Hire `technical-operator` for retainer-delivery work (that is a `koho-ops` / `yeh-ops` lane, ADR pending).
- Modify any existing profile.
- Build cron cadence. Smoke test fires once, manually, via `fleet-invoke.sh`.

## Authority Boundary (Hard Rules)

The profile must refuse, in its `CLAUDE.md` hard rules and again in `DOCTRINE.md`:

1. **No code edits.** Only critiques. The reviewing skill returns findings; the invoking operator applies any fix.
2. **No deploys, no merges, no force-pushes.** No git mutation. No CI re-runs. No environment variable changes.
3. **No external sends.** No email, no Slack post, no PR comments, no GitHub issues, no Sentry tickets. Output is inbox files only.
4. **No spending.** No tool calls that incur API spend on a non-Anthropic provider, no MCP write to billable services.
5. **No autonomous loop.** No retry-until-success. One invocation, one critique. If the critique cannot be produced, return a structured "blocked" output naming the missing input.
6. **No persona collapse.** Not a coder. Not Codex the tool. Not a CTO-roleplay. The profile is a procedural engineering review workflow with memory.

## Promotion Criteria (Future Slice)

To promote `technical-operator` to rung 2 (scoped tool actions with human approval gate), a separate ADR must show:

- ≥ 10 real critiques landed in the inbox over ≥ 2 weeks.
- Stet-equivalent kill-trigger discipline holds (a critique that would block a ship actually causes the ship to halt; false positives < 20%).
- One specific revenue product or paid-retainer surface justifies the scoped tool action (e.g., proposing Sentry triage tickets that a human approves).
- A spend cap and a kill-switch path are defined for the scoped action.

Rung 3+ requires another ADR per the agent-shape ADR.

## Reversibility

TYPE-2. `rm -rf hermes/profiles/technical-operator/ && git checkout scripts/build-agency-shared-skills.py` and `git checkout _meta/decisions/2026-05-20-technical-operator-profile-scope.md` undoes the slice in under a minute. The 20 inherited Agency skills are regenerated from upstream by re-running the build script — no data loss.

## 1% Engineer Move

Next 1% after this lands: fire one real `technical-review` against a Marin or Stet skill file, then capture the critique + PFOS row UUID in the pilot receipt. Don't build the second profile-local skill until the first review is reviewed by Alex.

Why it beats tempting alternatives: scaffolding more skills before the first one is judged by an operator is the YAGNI failure this ADR is designed to avoid.
