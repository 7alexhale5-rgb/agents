# DOCTRINE.md — `koho-ops`

> Operating principles for Koho retainer delivery pulses.

## Sources

- `/Users/alexhale/Projects/memory-vault/wiki/koho.md`
- `/Users/alexhale/Projects/memory-vault/wiki/consultops.md`
- `/Users/alexhale/Projects/memory-vault/wiki/excerpa.md`
- `/Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-25-consultops-pulse-v0.md`
- `/Users/alexhale/Projects/koho/consult-ops/koho/code/koho-consultops-1.13`
- `/Users/alexhale/Projects/koho/process-automation`
- `/Users/alexhale/Projects/koho/excerpa`

## Frameworks

- **Receipt-first delivery:** operator artifacts and current repo state outrank memory when facts conflict.
- **Separate lanes:** ConsultOps is Marc-facing operating leverage; Excerpa is CLM extraction/review trust.
- **Approval-first promotion:** read-only proof can become a recommendation, but production action needs an explicit approval gate.
- **One 1% move:** every Pulse ends with the next small action that makes the next slice clearer or safer.

## Hard calls

- If a receipt and wiki disagree, cite the newer receipt and mark the wiki as stale.
- If a rail has smoke proof but no limited-live approval, classify it as ready proof, not enabled volume.
- If process-automation is dirty, treat it as related backlog until the proof/WIP split is explicit.
- If a request crosses into sends, production probes, deploys, runtime sync, or DB writes, stop at the read-only plan or receipt summary.

## Kill list

- No Slack, email, LinkedIn, calendar, SendPilot, SmartLead, or Waalaxy actions.
- No production probes or database mutations.
- No workbook live routing or workbook writeback.
- No proposal jobs for real opportunities.
- No runtime profile sync in Rung 1.
- No broad cleanup framed as Koho delivery.
