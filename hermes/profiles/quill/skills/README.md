---
name: skills-registry
description: Quill skill registry — every skill is a flat MD file in this directory per the 11-file contract ADR.
---

# Quill skills

| Skill                       | Purpose                                                                                                     | Output target                                            |
| --------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| `draft-linkedin-field-note` | One LinkedIn post draft from WORKS Review public signal sprint context. First live skill — proves the loop. | `~/Projects/marketing/_inbox/quill-drafts/` + Hermes local receipt |
| `draft-outreach-message`    | Post-acceptance workflow-question DM (the campaign-authorized next move). Never cold outreach.              | `~/Projects/marketing/_inbox/quill-drafts/` + Hermes local receipt |
| `draft-campaign-asset`      | Scorecard section / landing-page copy / offer one-pager per active campaign brief.                          | `~/Projects/marketing/_inbox/quill-drafts/` + Hermes local receipt |
| `revise-from-critique`      | Reads a Stet critique from `_inbox/stet-critiques/` and produces a revised draft addressing each finding. | `~/Projects/marketing/_inbox/quill-drafts/` + Hermes local receipt |
| `generate-handoff` (shared) | Cross-session handoff per `hermes/shared-skills/generate-handoff/`.                                         | `~/Projects/memory-vault/handoffs/`                      |

## Skill conventions

- One flat `.md` per skill. No nested directories (lint enforced).
- Every skill that writes a draft MUST end with the explicit
  Hermes local receipt metadata for the produced inbox artifact.
- Every skill names the marketing vault inputs it reads in priority order.
- Every skill names the Content Rule completeness check before declaring done.

## Receipt pattern (every drafting skill)

```text
Write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
```

The receipt writer loads `config.yaml`'s `draft.propose.event` block, asserts ADR-compliant fields are present, then writes the local Hermes receipt for the inbox artifact. Returns the receipt ID on stdout, exit 0.
