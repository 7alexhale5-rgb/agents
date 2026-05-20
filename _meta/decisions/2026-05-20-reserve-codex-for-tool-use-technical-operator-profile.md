---
date: 2026-05-20
type: decision
project: agents
tags: [adr, hermes, profiles, codex, cto, technical-operator, yagni, sine]
status: accepted
supersedes:
  - _meta/ORG-CHART.md engineering row naming `codex` as a department head
  - docs/migration-runbook.md Phase 5.5 `codex` profile rebuild
  - docs/capability-roadmap.md references to rebuilding the `codex` profile
related_adrs:
  - 2026-05-18-agent-shape-11-file-contract.md
  - 2026-05-18-subproject-to-profile-trigger.md
  - 2026-05-16-agentic-os-hybrid-runtime-lanes.md
  - 2026-05-20-capability-build-sequence.md
---

# ADR: Reserve Codex For Tool Use; Replace Fleet Profile With Technical Operator Boundary

## Decision

Do not build or bless an autonomous Hermes profile named `codex`.

`Codex` means the OpenAI tool and operator-controlled coding lane Alex is using directly. It stays environment/tool scope (`~/.codex/`, Codex CLI/app, closeout/staged-review workflows), not Hermes fleet identity.

If PrettyFly later needs a durable engineering governance profile, the replacement is a `technical-operator` profile with display role `CTO / Technical Operator`. That profile may be created only after it has a real `$1M ARR` job: technical reliability, architecture governance, code review, Sentry/incident hygiene, release gates, and engineering QA/QC for revenue products or paid retainer delivery.

Until then, the existing `hermes/profiles/codex/` directory is a placeholder/name-collision artifact. Do not add new authority, channels, tools, runtime crons, or agency-skill ownership to it.

## Why

The fleet needs clean nouns.

Codex is already the thing Alex is using to do coding work. Reusing the same name for a Hermes agent blurs three boundaries:

1. **Tool vs agent:** Codex is an operator tool. Hermes profiles are durable identities with memory, contracts, routing, evals, and optional channels.
2. **Human technical judgment vs automation:** CTO-level work includes architecture, incident ownership, release risk, Sentry triage, and code-quality accountability. A generic "coding agent" is not enough.
3. **Revenue mission vs capability hoarding:** The current company goal is PrettyFly CTO Advisory to `$1M ARR` in 24 months. A new profile must unlock revenue, delivery, retention, reliability, or executive leverage.

This keeps SINE/SOLID/YAGNI/KISS/DRY intact:

- **SINE:** The role exists only if it moves the `$1M ARR` roadmap.
- **SOLID:** One profile has one reason to exist. `technical-operator` governs technical operations; it does not become marketing, sales, or COO.
- **YAGNI:** No autonomous engineering profile before real reliability or delivery load proves the need.
- **KISS:** Codex remains the tool. Hermes profiles remain business-role identities.
- **DRY:** Do not duplicate Codex the tool as Codex the agent.

## Hermes Fit

### Profile-vs-skill rule

Per the existing profile trigger ADR, a capability earns its own Hermes profile only when it needs durable identity, long-running state, isolated routing, and measurable gates.

Engineering checklists, review rubrics, Sentry triage notes, test plans, and release templates should start as skills or operator runbooks. They become a `technical-operator` profile only when recurring technical governance is large enough to justify memory, routing, tools, and evals.

### Runtime lanes

Per the hybrid-runtime-lanes ADR, `codex` remains a runtime lane for evidence emitted from operator-controlled Codex work. That lane may appear in PFOS as provenance, but it is not a Hermes profile.

Allowed wording:

- `runtime_lane: codex`
- `tool: Codex`
- `review source: Codex staged-review`

Disallowed wording:

- `profile: codex`
- `agent_id: codex`
- `Codex owns engineering`
- `Codex autonomous engineering agent`

### 11-file contract

If `technical-operator` is created, it must use the Atlas-derived 11-file contract. It starts at rung 1 unless a separate promotion gate says otherwise.

Minimum starting posture:

| Surface | Boundary |
| --- | --- |
| Channels | none by default |
| Authority | read-only or propose-only |
| Writes | `_inbox/technical-operator/` or equivalent proposal path only |
| Tools | no deploy, send, merge, spend, or prod mutation without explicit approval gate |
| Events | redacted PFOS events only |
| Gate | one real technical review or incident/postmortem proposal with matching PFOS event |

## Technical Operator Boundary

The future `technical-operator` profile may own:

- Architecture review for revenue products and paid delivery surfaces
- Code review policy and release-risk notes
- Sentry issue triage proposals
- Incident classification and postmortem drafts
- QA/QC checklists for shipping changes
- Performance and reliability review
- Technical debt prioritization tied to revenue or retention
- Evaluation of engineering agency/shared skills before opt-in

It must not own:

- Autonomous coding as a persona
- Direct deploys, merges, production mutations, or external sends
- Marketing strategy, sales outreach, or content drafting
- COO cadence, weekly business priorities, or task dispatch
- Generic "engineering department" behavior before the workload exists
- Tool identity for Codex, Claude Code, Cursor, or any other operator harness

## Org Fit

Current smallest correct operating model:

| Function | Owner |
| --- | --- |
| Final business decisions, client trust, offer, sales | Alex |
| Executive signal and CEO memo | `atlas-ceo` |
| Marketing revenue loop | `marin` |
| Drafting from approved positioning | `quill` |
| Claim and launch critique | `stet` |
| Operating cadence / QA pressure | future `vanclief-coo` process or profile, not old marketplace `vanclief` |
| Technical governance | fractional human CTO / Principal Engineer now; future `technical-operator` profile only when earned |
| Client delivery lanes | `koho-ops` / `yeh-ops` only when retainer load justifies them |

## Consequences

- The existing agency-skill consolidation must not treat `hermes/profiles/codex/` as blessed fleet identity.
- Any engineering Agency-derived skills currently mapped to `codex` need review before commit. They should be parked, mapped to future `technical-operator`, or left unowned until the profile exists.
- Root routing docs should be updated in a later focused cleanup to replace Phase 5.5 `codex` language with `technical-operator`, but this ADR is the source of truth immediately.
- Historical ADRs that mention `codex` as a 13-profile marketplace-era department head remain historical; do not edit them in place.

## 1% Engineer Move

Next best target: reconcile the dirty Agency skills consolidation against this ADR before committing it.

Why it beats tempting alternatives: the consolidation currently touches `hermes/profiles/codex/`, and committing those opt-ins would re-bless the exact naming mistake this ADR closes.

Expected confidence: high. The change is mostly ownership routing and documentation, with small blast radius if handled before commit.

Should wait: full profile rename, creating `hermes/profiles/technical-operator/`, human COO hiring, autonomous coding loops, and any deploy/merge authority.
