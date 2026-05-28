# changelog — `koho-ops`

## 0.3.1

- Added `source-freshness-checklist` as a read-only awareness skill.
- The checklist only names sources to read, observed freshness, repo state, stale or missing context, and the next source to inspect.
- Kept Koho-Ops on awareness-only footing: no write tools, event contracts, runtime sync, or workflow path.

## 0.3.0

- Corrected Koho-Ops from the old operating-agent framing to read-only project awareness.
- Removed action-promotion intent: no ConsultOps/Koho operation and no path toward workflow authority.
- Reframed `consultops-pulse` as an ear-to-the-ground status skill for source freshness, repo state, and update signals.

## 0.2.0

- Added the profile-local `consultops-pulse` skill as the first repeatable Rung 1 Koho-Ops workflow.
- Locked required reads to Koho-Ops profile docs, ConsultOps Pulse v0, Koho/ConsultOps wiki context, ConsultOps repo status/log, and `process-automation` status.
- Preserved read-only boundaries: no write contract, no runtime sync, no production probes, no sends, no deploys, and no database writes.

## 0.1.0

- Profile scaffolded from `hermes/skills/profile-from-template/`.
- Rung 1 (read-only): one source tool (`koho_context.read`), no write tools, no event contracts, no runtime sync.
- ConsultOps Pulse v0 named as the first operating source packet.
- Excerpa Pulse reserved as the second operating pattern.
- Superseded by 0.3.0: this profile stays awareness-only and should not add a workflow action path.
