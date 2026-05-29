# Skill: topic-sweep

The mcp-scout weekly sweep. One job: turn a week of agentic-patterns + MCP signal
into a source-grounded digest with a CI-rubric verdict per finding, and keep the
AI Agents & Orchestration NotebookLM notebook current.

## When to run

Weekly via cron (workdir = this profile). Also on demand when Alex asks "what's
new in MCP / agent orchestration."

## Inputs

- `DOCTRINE.md § Sources` — the canonical source list
- `DOCTRINE.md § CI verdict rubric` — the verdict enum + target rule
- Prior digests in `_inbox/mcp-scout/` — for delta tracking + dedup
- `~/Projects/agents/_meta/decisions/` + per-project `.mcp.json` — the "already-have-it" contract baseline
- Notebook `a4ca2b00` (AI Agents & Orchestration) — prior synthesized knowledge

## Procedure

1. **Auth liveness.** Run `notebooklm auth check`. If it fails, note "NB auth expired — run `notebooklm login`" and continue in vault-only mode (no ingestion this run). Never fail silent.

2. **Read the baseline.** Skim the most recent prior digest + the fleet's event-contract/agent-shape ADRs so findings are deltas, not restatements of patterns the fleet already implements.

3. **Sweep via research-stack.** Invoke:
   ```
   /research-stack --deep --youtube --vault --notebook a4ca2b00 "Agentic patterns + MCP — spec/registry movement, A2A protocols and signed agent cards, multi-agent orchestration (plan-execute-verify, verifier loops), notable agent papers/frameworks — since <last digest date>"
   ```
   This pulls web + YouTube transcripts, compresses, ingests the discovered source URLs into the notebook, and writes vault notes. Specs/registry/papers are weighted highest (primary, cited).

4. **Dedup + classify.** For each candidate finding: is it already in a fleet contract or a prior digest? If yes and unchanged → drop. If new or status-changed → keep, assign one CI-rubric verdict + a named target (cross-project architecture, a specific framework/server, or the PFOS runtime/A2A surface). Apply the reversibility lens: TYPE-1 cross-project contract changes cap at AUDIT/WAIT at rung 1.

5. **Write the digest** via `topic_digest.propose` to `_inbox/mcp-scout/{date}-digest.md` using the `DOCTRINE.md § Output contract` shape: delta line → quiet/active signal → numbered findings (each sourced, each with verdict + target) → "watch next" line. Emit the Hermes-local receipt (counts + notebook id + sources-ingested + digest path; never the body).

6. **Append the sweep ledger** line in `MEMORY.md`: date · findings · top verdict.

## Output

One digest at `_inbox/mcp-scout/{date}-digest.md` + one `mcp_scout.digest.proposed` receipt + N sources ingested into notebook `a4ca2b00`.

## Guardrails (from CLAUDE.md hard rules)

- Source-grounded or silent — never fabricate a spec change/version/capability.
- Verdict + target required per finding.
- Read-only on every repo and every contract; the digest + notebook ingestion are the only writes.
- No external sends; no finding execution. Routing into projects is rung 2+.

## Rung-1 acceptance signal

A run counts toward the gate when: the digest lands, ≥1 source ingested into the
notebook, `lint-profile.sh mcp-scout` PASSes, and the digest carries ≥1 verdict
with a named target. Two consecutive useful weekly digests → eligible for the
rung-2 promotion ADR.
