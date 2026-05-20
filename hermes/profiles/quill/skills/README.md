---
name: skills-registry
description: Quill skill registry — every skill is a flat MD file in this directory per the 11-file contract ADR.
---

# Quill skills

| Skill                       | Purpose                                                                                                     | Output target                                            |
| --------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `draft-linkedin-field-note` | One LinkedIn post draft from WORKS Review public signal sprint context. First live skill — proves the loop. | `~/Projects/marketing/_inbox/quill-drafts/` + PFOS event |
| `draft-outreach-message`    | Post-acceptance workflow-question DM (the campaign-authorized next move). Never cold outreach.              | `~/Projects/marketing/_inbox/quill-drafts/` + PFOS event |
| `draft-campaign-asset`      | Scorecard section / landing-page copy / offer one-pager per active campaign brief.                          | `~/Projects/marketing/_inbox/quill-drafts/` + PFOS event |
| `revise-from-critique`      | Reads a Viper critique from `_inbox/viper-critiques/` and produces a revised draft addressing each finding. | `~/Projects/marketing/_inbox/quill-drafts/` + PFOS event |
| `generate-handoff` (shared) | Cross-session handoff per `hermes/shared-skills/generate-handoff/`.                                         | `~/Projects/memory-vault/handoffs/`                      |

## Skill conventions

- One flat `.md` per skill. No nested directories (lint enforced).
- Every skill that writes a draft MUST end with the explicit
  `scripts/emit-agent-event.py` CLI call to fire the paired PFOS event.
- Every skill names the marketing vault inputs it reads in priority order.
- Every skill names the Content Rule completeness check before declaring done.

## Event emission pattern (every drafting skill)

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile quill \
  --tool <draft_field_note.propose|draft_outreach.propose|draft_campaign_asset.propose|draft_revision.propose> \
  --readout-path "_inbox/quill-drafts/<YYYY-MM-DD>-<type>-<slug>.md" \
  --extra-json '{"pillar":"<1-5>","sweeps_passed":true,"content_rule_complete":true}'
```

The emitter loads `config.yaml`'s `draft.propose.event` block, asserts ADR-compliant fields are present, then POSTs to PFOS `/api/silos/skills/agent-event`. Returns the row UUID on stdout, exit 0.
