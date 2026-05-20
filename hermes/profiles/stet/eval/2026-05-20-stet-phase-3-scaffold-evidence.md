---
date: 2026-05-20
type: eval-evidence
project: agents
agent: stet
phase: 3
status: scaffold-complete
---

# Stet Phase 3 scaffold evidence — 2026-05-20

## Scaffold status

- 11-file contract: PASS (lint clean)
- Skills: 5 flat MD (`README`, `critique-draft`, `critique-campaign-brief`, `critique-positioning`, `pressure-test-campaign`)
- Per-skill tool attribution: 4 distinct `<critique-name>.propose` tools in config.yaml, each with own event block (skill_slug correctly distinct per skill)
- Dry-run emitter check: ADR-compliant payload verified — `type=stet.critique.proposed`, `cwd_project=marketing`, `skill_slug=critique-draft`, `surface=cli`, `silo_slug=skills`, `data.runtime=hermes`, `data.proposal_status=proposed`, `data.private_payload_redacted=true`

## Eval suite

`promptfoo.yaml` configured with `anthropic:messages:claude-sonnet-4-6` (no exec proxy — Atlas's `pf-runtime/scripts/eval_profile_prompt.py` path is archived).

Six tests:

1. Every flagged finding cites a vault source by name
2. Every finding has a fix path or hard-block
3. Generic AI education request → verdict `KILL` with kill-list citation
4. Banned vocab (game-changing, AI-powered, 10x, etc.) → flagged in Voice sweep
5. Scaling without named workflow → verdict `KILL` with do-not-scale citation
6. Verdict is exactly one of `SHIP` / `REVISE` / `KILL`

System prompt fixture at `eval/fixtures/stet-system-prompt.md` distills SOUL + DOCTRINE + USER + MEMORY into a single context block.

Deliberately-bad draft fixture at `eval/fixtures/draft-with-3-anti-slop-violations.md` exercises Voice sweep, Proof sweep (invented evidence), CTA sweep (multi-ask), and false self-attestation detection.

## Phase 3 Karpathy gate

Falsifiable in one SQL query:

```sql
SELECT id, type, cwd_project, skill_slug, surface
FROM public.agent_events
WHERE type = 'stet.critique.proposed'
  AND cwd_project = 'marketing'
  AND skill_slug IS NOT NULL
  AND surface = 'cli'
  AND created_at > NOW() - INTERVAL '1 hour';
-- expect: ≥1 row
```

First real-emission evidence will be appended once `critique-draft` produces a critique that lands in `_inbox/stet-critiques/` and the matching event row exists in PFOS.
