# technical-operator skills

Profile-local skills for the `technical-operator` profile. At rung 1 (read-only),
the only profile-local skill is `technical-review`. Inherited engineering Agency
shared skills are listed in `manifest.json` and live under
`~/Projects/agents/hermes/shared-skills/agency/`.

| Skill              | Purpose                                                                                  | Output                                                                                           |
| ------------------ | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `technical-review` | Procedural engineering review of one target artifact (skill, script, ADR, plan, PR diff) | One markdown critique in `~/Projects/agents/_inbox/technical-operator-reviews/` + one PFOS event |

Promotion to a second profile-local skill requires a separate ADR per the scope
ADR (`_meta/decisions/2026-05-20-technical-operator-profile-scope.md`).
