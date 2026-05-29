# Skill: topic-sweep

The pkm-scout weekly sweep. One job: turn a week of NotebookLM + PKM signal into a
source-grounded digest with a CI-rubric verdict per finding, and keep the Personal
Automation NotebookLM notebook current.

## When to run

Weekly via cron (workdir = this profile). Also on demand when Alex asks "what's new
in NotebookLM / Obsidian / PKM."

## Inputs

- `DOCTRINE.md § Sources` — the canonical source list
- `DOCTRINE.md § CI verdict rubric` — the verdict enum + target rule
- Prior digests in `_inbox/pkm-scout/` — for delta tracking + dedup
- `~/Projects/memory-vault/wiki/` + `memory_hub.py` — the "already-have-it" second-brain baseline
- Notebook `f181b42e` (Personal Automation) — prior synthesized knowledge

## Procedure

1. **Auth liveness.** Run `notebooklm auth check`. If it fails, note "NB auth expired — run `notebooklm login`" and continue in vault-only mode (no ingestion this run). Never fail silent. A recurring auth failure is itself a reportable F-finding (this profile owns the `notebooklm-py` health beat).

2. **Read the baseline.** Skim the most recent prior digest + the memory-vault wiki so findings are deltas, not restatements of patterns the vault already implements.

3. **Sweep via research-stack.** Invoke:
   ```
   /research-stack --deep --youtube --vault --notebook f181b42e "NotebookLM + PKM — NotebookLM feature/API updates (watch for an official consumer API), Obsidian releases + Bases roadmap, second-brain methodology, notebooklm-py dependency health — since <last digest date>"
   ```
   This pulls web + YouTube transcripts, compresses, ingests the discovered source URLs into the notebook, and writes vault notes. Official Google/Obsidian blogs + the notebooklm-py repo are weighted highest (primary, cited).

4. **Dedup + classify.** For each candidate finding: is it already in the memory-vault wiki or a prior digest? If yes and unchanged → drop. If new or status-changed → keep, assign one CI-rubric verdict + a named target (memory-vault/research-vault workflows, `notebooklm-py`, env-global, or "watch"). Apply the reversibility lens: TYPE-1 vault-structure / dependency-replacement changes cap at AUDIT/WAIT at rung 1.

5. **Write the digest** via `topic_digest.propose` to `_inbox/pkm-scout/{date}-digest.md` using the `DOCTRINE.md § Output contract` shape: delta line → quiet/active signal → numbered findings (each sourced, each with verdict + target) → "watch next" line that always re-checks the official-NotebookLM-consumer-API question. Emit the Hermes-local receipt (counts + notebook id + sources-ingested + digest path; never the body).

6. **Append the sweep ledger** line in `MEMORY.md`: date · findings · top verdict.

## Output

One digest at `_inbox/pkm-scout/{date}-digest.md` + one `pkm_scout.digest.proposed` receipt + N sources ingested into notebook `f181b42e`.

## Guardrails (from CLAUDE.md hard rules)

- Source-grounded or silent — never fabricate a feature/version/API.
- Verdict + target required per finding.
- Read-only on every vault and repo; the digest + notebook ingestion are the only writes.
- No external sends; no finding execution. Routing into workflows is rung 2+.

## Rung-1 acceptance signal

A run counts toward the gate when: the digest lands, ≥1 source ingested into the
notebook, `lint-profile.sh pkm-scout` PASSes, and the digest carries ≥1 verdict
with a named target. Two consecutive useful weekly digests → eligible for the
rung-2 promotion ADR.
