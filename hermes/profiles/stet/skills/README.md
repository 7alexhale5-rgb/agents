---
name: skills-registry
description: Stet skill registry — every skill is a flat MD file in this directory per the 11-file contract ADR.
---

# Stet skills

| Skill                       | Purpose                                                                                                                  | Output target                                               |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `critique-draft`            | Critique one Quill draft in `_inbox/quill-drafts/`. Per-sweep findings, severity, fix-path or hard-block, verdict.       | `~/Projects/marketing/_inbox/stet-critiques/` + Hermes local receipt |
| `critique-campaign-brief`   | Critique one `campaigns/<name>/campaign-brief.md`. Apply kill-list, tool-trigger, do-not-scale, market-thesis tests.     | `~/Projects/marketing/_inbox/stet-critiques/` + Hermes local receipt |
| `critique-positioning`      | Critique one positioning claim against `market-thesis-v0.md`, `buyer-belief-ladder.md`, `channel-positioning-map-v0.md`. | `~/Projects/marketing/_inbox/stet-critiques/` + Hermes local receipt |
| `pressure-test-campaign`    | Pre-launch pressure test of a campaign — inversion + door classification + adversarial sweeps across the whole dir.      | `~/Projects/marketing/_inbox/stet-critiques/` + Hermes local receipt |
| `generate-handoff` (shared) | Cross-session handoff per `hermes/shared-skills/generate-handoff/`.                                                      | `~/Projects/memory-vault/handoffs/`                         |

## Skill conventions

- One flat `.md` per skill. No nested directories (lint enforced).
- Every skill that writes a critique MUST end with the explicit
  Hermes local receipt metadata for the produced inbox artifact.
- Every skill names the marketing vault inputs it reads in priority order.
- Every skill requires a verdict (`SHIP` / `REVISE` / `KILL`) in the
  output frontmatter AND body.
- Every flagged finding cites a specific vault file as its source.

## Receipt pattern (every critique skill)

```text
Write or verify the Hermes local receipt for the inbox artifact. Do not call the legacy PFOS emitter unless Alex explicitly reopens PFOS for this workflow.
```

The receipt writer loads `config.yaml`'s matching `<tool>.event` block, asserts ADR-compliant fields, writes the local Hermes receipt for the inbox artifact. Returns receipt ID on stdout, exit 0.
