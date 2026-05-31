# ADR: Capture Polsia as competitive intel & guardrail spec

- **Date:** 2026-05-30
- **Status:** accepted
- **Context:** Alex ran a deep research pass + live interrogation of Polsia (polsia.com), a $30M/$250M-valued "autonomous AI that runs your company" platform. Its 9-agent staggered-cadence design is a direct reference for our Hermes fleet, and its public failure modes (2.1/5 Trustpilot) are instructive.

## Decision

Consolidate all Polsia research into `docs/competitive-intel/polsia/` (tracked) rather than leaving it in `memory-vault/operator-artifacts/` and `research-vault/`. Treat it as a reusable design reference — "great artists steal."

## What we're stealing

1. **Staggered per-agent cadence** as a first-class scheduler concept (2h/3h/6h/daily/on-demand).
2. **Day-bookend orchestration** — morning plan + evening summary (we have morning-logs; add the evening pass).
3. **Live activity stream** — a glanceable feed of autonomous work (Polsia's best UX).
4. **Atomic, logged tasks** with retrievable execution logs at the action grain.
5. **The SEO/AEO task catalog** — reusable as Quill/Marin `SKILL.md` skills, run on our grounded stack instead of per-credit.

## What we're rejecting (and why our design already prevents it)

Polsia's failure modes become a **negative test-suite** for the fleet:
- Autonomous publishing without approval → our Quill never publishes; Karpathy rung ladder.
- No validation gate before acting → Atlas/Stet pressure-test first.
- "Complete" tasks that never deployed → review-stack "verify the user-visible artifact."

**Meta-lesson:** autonomy without gates is a reputational liability. The Karpathy ladder (rung 1 read-only → rung 4 gated actions) is the correct spine; this is evidence to keep it.

## Consequences / follow-ups

- Turn top SEO/AEO prompts into a `quill` skill.
- Add an evening-summary pass to `morning-logs`.
- Add `cadence:` to profile entries in `_meta/agent-fleet-spec.md`.
- Add a fleet eval: "no rung-≤3 profile produces an external side-effect" (Polsia failures as negative fixtures).

## Provenance

Full intel: `docs/competitive-intel/polsia/`. Captured via live dashboard interrogation (Alex's trial account, ends 2026-06-27) + Perplexity/Firecrawl/web research.
