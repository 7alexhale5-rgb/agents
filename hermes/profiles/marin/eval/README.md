# Marin eval suite

Four fixtures testing weekly-review decision routing. Each fixture provides a synthetic vault state; Marin must produce a readout proposing the correct decision.

| Fixture       | Vault state                                                                                                                                                 | Expected decision                                                  |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `continue.md` | Routes opened: 8, named workflow: 1 ("integration-heavy ConsultOps client wants Marc routing for compliance reviews"), buyer language getting more specific | `continue` (with note: keep ICP + message angle + channel)         |
| `narrow.md`   | Routes opened: 12, replies from 3 segments, segment A (operator-led 75-person consultancies) produces 2 named workflows vs 0 in segments B/C                | `narrow ICP` to segment A                                          |
| `rewrite.md`  | Routes opened: 10, replies but all variants of "we already have AI" — no pain resonance                                                                     | `rewrite message` to lead with operational drag, not AI capability |
| `pause.md`    | Routes opened: 0, no replies, no Field Notes published, no diagnostics, no WORKS Reviews                                                                    | `pause` (and "collect smallest signal")                            |

## Gate

≥80% pass rate on both Haiku 4.5 and Sonnet 4.6. Failures must show "right decision, wrong rationale" not "wrong decision."

## Anti-fabrication check

Every fixture also tests: does Marin invent buyer names, reply counts, or workflow language not present in the vault fixture? Any fabrication = fail, regardless of decision correctness.

## Run

Primary config: `eval/promptfoo.yaml`.

Buyer-signal router config: `eval/buyer-signal-router.promptfoo.yaml`.

Run with Promptfoo when model credentials are available:

```bash
promptfoo eval -c hermes/profiles/marin/eval/promptfoo.yaml
promptfoo eval -c hermes/profiles/marin/eval/buyer-signal-router.promptfoo.yaml
```

If model credentials are unavailable, validate the fixtures structurally and run the dogfood readout gate before promotion.
