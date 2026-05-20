---
date: 2026-05-20
type: eval-evidence
project: agents
agent: quill
phase: 3
status: scaffold-complete
---

# Quill Phase 3 scaffold evidence — 2026-05-20

## Scaffold status

- 11-file contract: PASS (lint clean)
- Skills: 5 flat MD (`README`, `draft-linkedin-field-note`, `draft-outreach-message`, `draft-campaign-asset`, `revise-from-critique`)
- Per-skill tool attribution: 4 distinct `draft_*.propose` tools in config.yaml, each with own event block (skill_slug correctly distinct per skill)
- Dry-run emitter check: ADR-compliant payload verified — `type=quill.draft.proposed`, `cwd_project=marketing`, `skill_slug=draft-linkedin-field-note`, `surface=cli`, `silo_slug=skills`, `data.runtime=hermes`, `data.proposal_status=proposed`, `data.private_payload_redacted=true`

## Eval suite

`promptfoo.yaml` configured with `anthropic:messages:claude-sonnet-4-6` (no exec proxy — Atlas's `pf-runtime/scripts/eval_profile_prompt.py` path is archived).

Six tests:

1. Field-note draft cites at least one vault source by name
2. No first-touch calendar / "book a call" / DM-me CTAs
3. No banned vocab (10x, unlock, AI-powered, etc.)
4. Generic AI education request refused (kill list)
5. Cold DM to non-selected prospect refused (campaign authorization)
6. Unproven 73% claim flagged ("source signal: none provided" or equivalent)

System prompt fixture at `eval/fixtures/quill-system-prompt.md` — distills SOUL + DOCTRINE + USER + MEMORY into a single context block that promptfoo injects for each test.

## Phase 3 Karpathy gate

Falsifiable in one SQL query:

```sql
SELECT id, type, cwd_project, skill_slug, surface
FROM public.agent_events
WHERE type = 'quill.draft.proposed'
  AND cwd_project = 'marketing'
  AND skill_slug IS NOT NULL
  AND surface = 'cli'
  AND created_at > NOW() - INTERVAL '1 hour';
-- expect: ≥1 row
```

First real-emission evidence will be appended to this file once `draft-linkedin-field-note` produces a Field Note that lands in `_inbox/quill-drafts/` and the matching event row exists in PFOS.
