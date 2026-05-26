# MEMORY.md — koho-ops environment facts

> Bounded character budget (~2,200 chars). Curated by the agent over time.

## Tooling

- `koho_context.read` is the only declared source-read tool in this scaffold.
- Current profile has no propose-write tool and no runtime sync in this slice.
- ConsultOps source repo: `/Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13`.
- Process-automation repo: `/Users/alexhale/Projects/koho/process-automation`.
- Memory-vault operator artifacts are the current receipt surface.

## Conventions

- Future local readouts should land under `/Users/alexhale/Projects/agents/_inbox/koho-ops/` only after a proposed-write contract exists.
- ConsultOps Pulse format: current answer, ready proof, approval needed, do not enable yet, repo/source state, next 1% move.
- Keep ConsultOps and Excerpa separate even when both sit under the Koho relationship.

## Recent decisions

- 2026-05-25: ConsultOps Pulse v0 committed in memory-vault as read-only operator receipt.
- 2026-05-25: Koho-ops scaffold starts at Rung 1, source-grounded and approval-first, with ConsultOps Pulse as first operating pattern.
