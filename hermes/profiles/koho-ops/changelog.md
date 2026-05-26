# changelog — `koho-ops`

## 0.2.0

- Added the profile-local `consultops-pulse` skill as the first repeatable Rung 1 Koho-Ops workflow.
- Locked required reads to Koho-Ops profile docs, ConsultOps Pulse v0, Koho/ConsultOps wiki context, ConsultOps repo status/log, and `process-automation` status.
- Preserved read-only boundaries: no propose-write contract, no runtime sync, no production probes, no sends, no deploys, and no database writes.

## 0.1.0

- Profile scaffolded from `hermes/skills/profile-from-template/`.
- Rung 1 (read-only): one source tool (`koho_context.read`), no propose-write tools, no event contracts, no runtime sync.
- ConsultOps Pulse v0 named as the first operating source packet.
- Excerpa Pulse reserved as the second operating pattern.
- Next step: add a Hermes-local proposed-write contract before this profile writes `_inbox/koho-ops/` work product.
