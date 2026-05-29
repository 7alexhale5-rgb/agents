# Skill: topic-sweep

The hermes-scout weekly sweep. One job: turn a week of Hermes-runtime signal into
a source-grounded digest with a CI-rubric verdict per finding, and keep the
Hermes Runtime NotebookLM notebook current.

## When to run

Weekly via cron (workdir = this profile). Also on demand when Alex asks "what's
new in Hermes."

## Inputs

- `DOCTRINE.md § Sources` — the canonical source list
- `DOCTRINE.md § CI verdict rubric` — the verdict enum + target rule
- Prior digests in `_inbox/hermes-scout/` — for delta tracking + dedup
- `~/Projects/agents/docs/capability-roadmap.md` — the already-evaluated baseline
- Notebook `771c0174` (Hermes Runtime) — prior synthesized knowledge

## Procedure

1. **Auth liveness.** Run `notebooklm auth check`. If it fails, note "NB auth expired — run `notebooklm login`" and continue in vault-only mode (no ingestion this run). Never fail silent.

2. **Read the baseline.** Skim the most recent prior digest + the capability roadmap so findings are deltas, not restatements of known items.

3. **Sweep via research-stack.** Invoke:
   ```
   /research-stack --deep --youtube --vault --notebook 771c0174 "Hermes Agent runtime — releases, Nous roadmap, community patterns (OMH, Labyrinth, ACP, incident-commander), peer-creator technique — since <last digest date>"
   ```
   This pulls web + YouTube transcripts, compresses, ingests the discovered source URLs into the Hermes Runtime notebook, and writes vault notes. NotebookLM is weighted highest (grounded, cited).

4. **Dedup + classify.** For each candidate finding: is it already in the capability roadmap or a prior digest? If yes and unchanged → drop. If new or status-changed → keep, assign one CI-rubric verdict + a named target (`agents/` repo, PFOS cockpit, or env-global). Apply the reversibility lens: TYPE-1 changes to `agents/` cap at AUDIT/WAIT at rung 1.

5. **Write the digest** via `topic_digest.propose` to `_inbox/hermes-scout/{date}-digest.md` using the `DOCTRINE.md § Output contract` shape: delta line → quiet/active signal → numbered findings (each sourced, each with verdict + target) → "watch next" line. Emit the Hermes-local receipt (counts + notebook id + sources-ingested + digest path; never the body).

6. **Append the sweep ledger** line in `MEMORY.md`: date · findings · top verdict.

## Output

One digest at `_inbox/hermes-scout/{date}-digest.md` + one `hermes_scout.digest.proposed` receipt + N sources ingested into notebook `771c0174`.

## Guardrails (from CLAUDE.md hard rules)

- Source-grounded or silent — never fabricate a release/version/capability.
- Verdict + target required per finding.
- Read-only on every repo; the digest + notebook ingestion are the only writes.
- No external sends; no finding execution. Routing into projects is rung 2+.

## Rung-1 acceptance signal

A run counts toward the gate when: the digest lands, ≥1 source ingested into the
notebook, `lint-profile.sh hermes-scout` PASSes, and the digest carries ≥1 verdict
with a named target. Two consecutive useful weekly digests → eligible for the
rung-2 promotion ADR.
