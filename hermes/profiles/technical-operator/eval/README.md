# technical-operator eval

Eval suite for the `technical-operator` profile. Promptfoo fixtures land here as
the profile accumulates real critiques in `~/Projects/agents/_inbox/technical-operator-reviews/`.

## Seed fixtures (planned, not yet authored)

1. **clean-skill-file** — a skill file with no doctrine violations; expect verdict
   `SHIP-RISK-LOW` and zero findings.
2. **missing-event-contract** — a skill file that emits a PFOS event whose `type`
   is not documented in the parent profile's `CLAUDE.md`; expect at least one
   `SHIP-RISK-MEDIUM` finding citing event contract conformance.
3. **hidden-authority-creep** — a config.yaml change adding a tool with a
   `write_scope` outside the profile's existing inbox; expect `BLOCK` finding.
4. **type-1-without-rollback** — a build script that mutates a remote DB
   without a documented rollback; expect `BLOCK` finding citing margin of
   safety.
5. **clean-adr** — a well-formed ADR with valid `related_adrs:` and
   reversibility classification; expect `SHIP-RISK-LOW`.

Fixtures will be authored after the first real critique lands per the scope
ADR's 1% engineer move.

## Promptfoo config

The promptfoo.yaml will be added when fixtures are written. Until then, the
acceptance gate is the single live SQL-verifiable critique + PFOS row described
in `CLAUDE.md § Acceptance gate (rung 1 ship)`.
