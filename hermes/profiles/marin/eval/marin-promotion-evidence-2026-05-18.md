# Marin Promotion Evidence - 2026-05-18

## Current Status

- Profile: `marin` / Marin
- Current rung: rung 2, propose-only
- Capability under review: `buyer-signal-router`
- Decision: keep Marin at rung 2 for buyer-signal routing. Weekly readout judgment passed product review, and buyer-signal-router now clears the synthetic eval gate, but rung 3 still requires real route-open/reply evidence plus Alex acceptance of recommendation quality.

## Evidence

- Weekly decision readout gate: passed. Alex confirmed the first AI Ops Audit weekly readout's `continue, hold volume, wait for route` judgment was accurate.
- Weekly decision eval: `promptfoo eval -c hermes/profiles/marin/eval/promptfoo.yaml --no-cache` passed 8/8 on 2026-05-18 after this hardening slice.
- Buyer-signal-router pre-hardening eval: 7/14 on 2026-05-18. Smoke route passed all seven fixtures; Sonnet failed all seven because labels were rendered as bold Markdown and underscores were escaped. One semantic risk also appeared: the accepted/no-reply case treated an approved workflow-question DM artifact as a named workflow.
- Buyer-signal-router post-hardening eval: `promptfoo eval -c hermes/profiles/marin/eval/buyer-signal-router.promptfoo.yaml --no-cache` passed 14/14 on 2026-05-18 across Haiku and Sonnet.
- Dogfood baseline: current three live connection notes must route to wait / route not open / named workflow none / proposed reply none / no workaround DM.
- Live dogfood memo: `~/Projects/marketing/_inbox/marin-readouts/2026-05-18-buyer-signal-current-three.md` routes the current three connection-note records to wait / route not open / named workflow none / proposed reply none / no workaround DM.
- Static safety scan after the passing eval found 0 unsafe output hits, 0 accepted/no-reply named-workflow artifact hits, and 0 non-`none` proposed replies for dogfood/negative/stop outputs.

## Hardening Decision

The next gate is Marin-local only:

- Keep text memo output, not JSON.
- Add field-level assertions that normalize presentation while still requiring plain one-line fields.
- Add a hard accepted/no-reply rule: approved messages, DM labels, and workflow-question DM artifacts are not named workflows.
- Keep `Proposed reply` constrained to `none`, an exact approved vault message reference, or a one-sentence manual reply intent.
- Do not add a COO profile, Quill/Viper scaffold, PFOS screen, CRM, automation, or global promotion framework in this slice.

## Promotion Rule

Marin can be considered for the next Karpathy rung for buyer-signal routing only after:

- buyer-signal-router eval passes 14/14 across smoke and Sonnet;
- dogfood current-three-notes output preserves the wait/no-route/no-workflow/no-reply decision;
- no output recommends automation, external sends, PFOS/CRM/tooling work, scraping, cold email, bulk Apollo, publishing, or volume increase;
- at least one real route-open or reply case is reviewed by Alex and accepted as good judgment.

## Next 1% Queue

1. Ask Alex to accept or reject the live current-three dogfood memo.
2. When the first route opens or reply arrives, run Marin on that live signal and record Alex's acceptance or correction.
3. Only after the live route/reply case is accepted, plan the next profile move; Viper rung 1 is the likely candidate, while Quill waits for buyer language.

## Audit Notes

| Date | Reviewer | Severity | Finding | Action | Status |
| --- | --- | --- | --- | --- | --- |
| 2026-05-18 | Codex | medium | Sonnet buyer-signal-router failures were mostly output-shape issues, but the accepted/no-reply case exposed a real risk of confusing approved message artifacts with named workflows. | Harden output contract and field-level eval assertions before promotion. | completed |
| 2026-05-18 | Codex | low | The OpenRouter/NVIDIA smoke route leaked reasoning and mangled fields, so it was not a reliable Haiku-equivalent promotion gate. | Use actual `anthropic:claude-haiku-4-5` alongside Sonnet for Marin eval gates. | completed |
