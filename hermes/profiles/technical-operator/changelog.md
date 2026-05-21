# Changelog — technical-operator profile

## 2026-05-20 — rung 1 scaffold

- Created via direct write (no `scripts/bootstrap-profile.sh` run); 11-file
  Atlas contract.
- Locked at rung 1 (read-only on review target, propose-only writes to
  `~/Projects/agents/_inbox/technical-operator-reviews/`).
- Channels: none.
- Authority: `technical_review.propose` only. No deploy, merge, send, or
  production-mutation tools.
- Inherited 20 engineering Agency shared skills previously parked under
  `PARKED_CANDIDATES["technical-operator"]` in
  `scripts/build-agency-shared-skills.py`. Build script updated to move them
  from parked to active under this profile.
- One profile-local skill: `technical-review`.
- Event type: `technical_operator.review.proposed`. Underscore form chosen for
  consistency with existing fleet events (`marin.*`, `stet.*`, `atlas.*`).
- Scope ADR: `_meta/decisions/2026-05-20-technical-operator-profile-scope.md`.
- Codex-boundary ADR: `_meta/decisions/2026-05-20-reserve-codex-for-tool-use-technical-operator-profile.md`.
- Smoke target: existing skill files in `hermes/profiles/marin/skills/` or
  `hermes/profiles/stet/skills/`.
- Promotion to rung 2+ requires a separate ADR.
