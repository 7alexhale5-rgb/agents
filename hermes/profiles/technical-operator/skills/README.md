# technical-operator skills

Profile-local skills for the `technical-operator` profile. At rung 1 (read-only),
profile-local skills must stay propose-only and write only to
`~/Projects/agents/_inbox/technical-operator-reviews/`. Inherited engineering Agency
shared skills are listed in `manifest.json` and live under
`~/Projects/agents/hermes/shared-skills/agency/`.

| Skill                   | Purpose                                                                                       | Output                                                                                                           |
| ----------------------- | --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `technical-review`      | Procedural engineering review of one target artifact (skill, script, ADR, plan, PR diff)      | One markdown critique in `~/Projects/agents/_inbox/technical-operator-reviews/` + one Hermes local receipt                 |
| `coding-session-review` | Read-only coding-session receipt: change surface, validation evidence, risks, next 1% move    | One markdown session receipt in `~/Projects/agents/_inbox/technical-operator-reviews/` + existing Hermes local receipt    |

`coding-session-review` is authorized by
`_meta/decisions/2026-05-22-technical-operator-coding-session-review-skill.md`.
