---
name: skills-registry
description: Stet skill registry — every skill is a flat MD file in this directory per the 11-file contract ADR.
---

# Stet skills

| Skill                       | Purpose                                                                                                                  | Output target                                               |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------- |
| `critique-draft`            | Critique one Quill draft in `_inbox/quill-drafts/`. Per-sweep findings, severity, fix-path or hard-block, verdict.       | `~/Projects/marketing/_inbox/stet-critiques/` + PFOS event |
| `critique-campaign-brief`   | Critique one `campaigns/<name>/campaign-brief.md`. Apply kill-list, tool-trigger, do-not-scale, market-thesis tests.     | `~/Projects/marketing/_inbox/stet-critiques/` + PFOS event |
| `critique-positioning`      | Critique one positioning claim against `market-thesis-v0.md`, `buyer-belief-ladder.md`, `channel-positioning-map-v0.md`. | `~/Projects/marketing/_inbox/stet-critiques/` + PFOS event |
| `pressure-test-campaign`    | Pre-launch pressure test of a campaign — inversion + door classification + adversarial sweeps across the whole dir.      | `~/Projects/marketing/_inbox/stet-critiques/` + PFOS event |
| `generate-handoff` (shared) | Cross-session handoff per `hermes/shared-skills/generate-handoff/`.                                                      | `~/Projects/memory-vault/handoffs/`                         |

## Skill conventions

- One flat `.md` per skill. No nested directories (lint enforced).
- Every skill that writes a critique MUST end with the explicit
  `scripts/emit-agent-event.py` CLI call to fire the paired PFOS event.
- Every skill names the marketing vault inputs it reads in priority order.
- Every skill requires a verdict (`SHIP` / `REVISE` / `KILL`) in the
  output frontmatter AND body.
- Every flagged finding cites a specific vault file as its source.

## Event emission pattern (every critique skill)

```bash
python3 /Users/alexhale/Projects/agents/scripts/emit-agent-event.py \
  --profile stet \
  --tool <critique_draft.propose|critique_campaign.propose|critique_positioning.propose|pressure_test.propose> \
  --readout-path "_inbox/stet-critiques/<YYYY-MM-DD>-critique-<slug>.md" \
  --extra-json '{"verdict":"<SHIP|REVISE|KILL>","critical":<N>,"warn":<N>,"info":<N>,"kill_triggers_hit":["..."],"target_artifact_path":"<path>"}'
```

The emitter loads `config.yaml`'s matching `<tool>.event` block, asserts ADR-compliant fields, POSTs to PFOS `/api/silos/skills/agent-event`. Returns row UUID on stdout, exit 0.
