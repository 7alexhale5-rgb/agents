# MEMORY.md — koho-ops environment facts

> Bounded character budget (~2,200 chars). Curated by the agent over time.

## Tooling

- `koho_context.read` is the only declared source-read tool in this scaffold.
- Current profile has no write tool, no runtime sync, and no action authority.
- ConsultOps source repo: `/Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13`.
- Process-automation repo: `/Users/alexhale/Projects/koho/process-automation`.
- Memory-vault operator artifacts are the current receipt surface.

## Conventions

- Manual local awareness notes may land under `/Users/alexhale/Projects/agents/_inbox/koho-ops/` when Alex asks.
- ConsultOps awareness format: current state, source updates, repo/source state, stale or missing context, boundaries, next check.
- Keep ConsultOps and Excerpa separate even when both sit under the Koho relationship.

## Recent decisions

- 2026-05-25: ConsultOps Pulse v0 committed in memory-vault as read-only operator receipt.
- 2026-05-26: Alex corrected the intent: Koho-ops is an ear-to-the-ground awareness profile only. It must not recommend or operate ConsultOps, Koho, Excerpa, or client workflows.
