# Skill: topic-sweep

The cc-scout weekly sweep. One job: turn a week of Claude Code + Anthropic signal
into a source-grounded digest with a CI-rubric verdict per finding, and keep the
AI Automation & LLMs NotebookLM notebook current.

## When to run

Weekly via cron (workdir = this profile). Also on demand when Alex asks "what's
new in Claude Code / Anthropic."

## Inputs

- `DOCTRINE.md § Sources` — the canonical source list
- `DOCTRINE.md § CI verdict rubric` — the verdict enum + target rule
- Prior digests in `_inbox/cc-scout/` — for delta tracking + dedup
- `~/.claude/CLAUDE.md` + `~/CLAUDE.md` + `~/.claude/references/` — the env-global "already-have-it" baseline
- Notebook `988d6e87` (AI Automation & LLMs) — prior synthesized knowledge

## Procedure

1. **Auth liveness.** Run `notebooklm auth check`. If it fails, note "NB auth expired — run `notebooklm login`" and continue in vault-only mode (no ingestion this run). Never fail silent.

2. **Read the baseline.** Skim the most recent prior digest + the env-global config so findings are deltas, not restatements of features Alex already runs.

3. **Sweep via research-stack.** Invoke:
   ```
   /research-stack --deep --youtube --vault --notebook 988d6e87 "Claude Code + Anthropic — new CC features (hooks, skills, subagents, slash commands, settings, plan/effort/output modes), Claude Agent SDK changes, Anthropic model releases — since <last digest date>"
   ```
   This pulls web + YouTube transcripts, compresses, ingests the discovered source URLs into the notebook, and writes vault notes. Anthropic changelog/docs are weighted highest (primary, cited).

4. **Dedup + classify.** For each candidate finding: is it already in the env-global config or a prior digest? If yes and unchanged → drop. If new or status-changed → keep, assign one CI-rubric verdict + a named target (env-global `~/.claude/`, a project, or the model-routing/SDK surface). Apply the reversibility lens: TYPE-1 env-global changes cap at AUDIT/WAIT at rung 1.

5. **Write the digest** via `topic_digest.propose` to `_inbox/cc-scout/{date}-digest.md` using the `DOCTRINE.md § Output contract` shape: delta line → quiet/active signal → numbered findings (each sourced, each with verdict + target) → "watch next" line. Emit the Hermes-local receipt (counts + notebook id + sources-ingested + digest path; never the body).

6. **Append the sweep ledger** line in `MEMORY.md`: date · findings · top verdict.

## Output

One digest at `_inbox/cc-scout/{date}-digest.md` + one `cc_scout.digest.proposed` receipt + N sources ingested into notebook `988d6e87`.

## Guardrails (from CLAUDE.md hard rules)

- Source-grounded or silent — never fabricate a feature/version/model/capability.
- Verdict + target required per finding.
- Read-only on every repo and on `~/.claude/`; the digest + notebook ingestion are the only writes.
- No external sends; no finding execution. Routing into projects/env is rung 2+.

## Rung-1 acceptance signal

A run counts toward the gate when: the digest lands, ≥1 source ingested into the
notebook, `lint-profile.sh cc-scout` PASSes, and the digest carries ≥1 verdict
with a named target. Two consecutive useful weekly digests → eligible for the
rung-2 promotion ADR.
