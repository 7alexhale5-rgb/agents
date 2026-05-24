# Atlas Promptfoo Reproof — 2026-05-24

Status: hiring eval gate re-proven on direct Anthropic provider.

## Why this exists

Atlas's Promptfoo graduation eval had been blocked by an archived
`pf-runtime/scripts/eval_profile_prompt.py` provider path. The eval now runs
directly against `anthropic:messages:claude-sonnet-4-6`, so the hiring eval can
be used again as rung-promotion evidence instead of being treated as stale
fallback proof.

## Verified run

Command:

```bash
cd /Users/alexhale/Projects/agents/hermes/profiles/atlas-ceo/eval
source ~/.config/api-keys.env
promptfoo eval -c promptfoo.yaml --no-cache -o /tmp/atlas-promptfoo-final-pass.json
```

Result:

- Eval id: `eval-6FQ-2026-05-24T03:03:26`
- Provider: `anthropic:messages:claude-sonnet-4-6`
- Cache: disabled
- Cases: 7
- Passed: 7
- Failed: 0
- Errors: 0
- Pass rate: 100%
- Token usage: 11,762 total

## What changed

- Atlas now injects `fixtures/fleet-source-packet.json` into the prompt for
  source-backed cases instead of asking Anthropic to read a local fixture path.
- The no-source refusal contract now requires the exact plain-text phrase
  `insufficient verified signal` and avoids listing unavailable metric names in
  the refusal.
- Decision-memo and approval-proposal contracts now state the exact strings the
  eval guards: lower-case `one-way` / `two-way`, `approval`, `proposed`, and no
  use of `executed`.

## Promotion read

This re-proves Atlas acceptance gate 7 from `CLAUDE.md`: "Atlas passes 90% of
the hiring eval suite with zero fabricated metrics." The current run clears it
at 100% with zero provider errors.

This does not by itself promote Atlas to routine action. It only removes the
eval-provider blocker from the promotion conversation. The remaining promotion
conversation should explicitly decide whether the existing 2026-05-18 Slack,
premium-route, adoption, and proposed-only receipt evidence is still fresh
enough, or whether those live gates need a new smoke pass.

## Next 1% move

Prepare the promotion packet, not another eval patch:

1. Cite this reproof as the current hiring-eval result.
2. Cite the 2026-05-18 premium-route and adoption evidence as historical live
   proof.
3. Mark the only open decision: whether to re-smoke Slack/proposed-only receipt
   before any rung-4 authority change.

