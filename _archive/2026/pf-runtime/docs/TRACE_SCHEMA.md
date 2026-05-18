# PF Runtime trace schema (canonical)

**Status**: DRAFT (lands in Phase 4.7.0 closeout, post-swarm-review)
**Authority**: any span emitted by PF Runtime OR by Hermes during the G1 baseline window MUST conform to this schema. Spans missing required attributes fail the contract test in `tests/trace_schema_contract.py`.
**Audience**: PF Runtime loop primitive (sub-phase 4.7.1), all adapters, all skills, all G1 capture script outputs.

## Why this exists

The G1 Hermes baseline and the 4.7.1 PF Runtime token-delta gate compare numbers across two different runtimes. Without a single attribute schema, the comparison is non-comparable — Hermes might emit `tokens.input` while PF Runtime emits `prompt_tokens`. This doc is the bridge.

It also feeds:

- the `~/Projects/agents/scripts/g1-baseline-capture.sh` row format (one column per required attribute).
- the cost-attribution join `langfuse.trace.profile_slug ↔ litellm.spend_log.api_key_alias` named in plan §5.9.
- the cross-profile contamination assertion in §5.9.8 (filter by `profile_slug`).

## Required span attributes (every span)

| Attribute                   | Type   | Example                                                                                                                             | Reason                                                                                               |
| --------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `pf_runtime.profile_slug`   | string | `personal`, `atlas-ceo`, `personal-baseline`                                                                                        | Tenant identity for cost attribution + isolation contracts                                           |
| `pf_runtime.session_id`     | string | `20260506_152300_abc12345`                                                                                                          | Group spans into the `state.db.sessions.id` row that triggered them                                  |
| `pf_runtime.runtime`        | enum   | `hermes-0.12.0` or `pf-runtime-0.1.0`                                                                                               | Distinguish which runtime produced the trace; required for G1 vs 4.7.1 comparison                    |
| `pf_runtime.runtime_commit` | string | `abc1234` (short hash)                                                                                                              | Pin the exact build emitting the trace; closes silent-version-drift                                  |
| `pf_runtime.span_kind`      | enum   | `loop_iteration`, `tool_call`, `llm_call`, `memory_read`, `memory_write`, `channel_inbound`, `channel_outbound`, `skill_invocation` | Coarse classification for filtering; do not invent values outside this list without a SPEC amendment |
| `pf_runtime.schema_version` | int    | `1`                                                                                                                                 | Bump on every schema change; capture script writes the same int to `HERMES_BASELINE.md` rows         |

## Required attributes — `llm_call` spans

| Attribute            | Type   | Reason                                                                                      |
| -------------------- | ------ | ------------------------------------------------------------------------------------------- |
| `llm.provider`       | enum   | `openrouter`, `anthropic`, `openai`, `litellm`, `local`                                     |
| `llm.model`          | string | E.g. `nvidia/nemotron-nano-9b-v2`; the resolved model, not the routing alias                |
| `llm.tier`           | enum   | `cheap`, `drafting`, `reasoning`, `strategic` (matches `personal/config.yaml` routing keys) |
| `llm.api_key_alias`  | string | LiteLLM key alias when routing through LiteLLM; otherwise `direct`                          |
| `tokens.input`       | int    | Includes prompt tokens; excludes cache reads                                                |
| `tokens.output`      | int    | Completion tokens                                                                           |
| `tokens.cache_read`  | int    | Anthropic cache-read tokens; 0 if N/A                                                       |
| `tokens.cache_write` | int    | Anthropic cache-write tokens; 0 if N/A                                                      |
| `tokens.reasoning`   | int    | Reasoning tokens (Claude extended thinking); 0 if N/A                                       |
| `cost.usd_estimated` | float  | Pre-billing-confirmation estimate                                                           |
| `cost.usd_actual`    | float  | Post-billing-confirmation; null until LiteLLM ledger reconciles                             |
| `latency.ms`         | int    | Wall-clock from request-send to response-complete                                           |

## Required attributes — `tool_call` spans

| Attribute             | Type   | Reason                                                                                            |
| --------------------- | ------ | ------------------------------------------------------------------------------------------------- |
| `tool.name`           | string | E.g. `obsidian_read`, `calendar_create_event`                                                     |
| `tool.server`         | string | MCP server name, A2A peer name, or `builtin`                                                      |
| `tool.arguments_hash` | string | sha256 of normalized arguments — do NOT log raw arguments (PII risk)                              |
| `tool.success`        | bool   | True if tool returned without error                                                               |
| `tool.error_class`    | string | When `success=false`, one of: `auth`, `not_found`, `rate_limit`, `validation`, `timeout`, `other` |
| `latency.ms`          | int    |                                                                                                   |

## Required attributes — `channel_inbound` / `channel_outbound` spans

| Attribute                   | Type   | Reason                                                            |
| --------------------------- | ------ | ----------------------------------------------------------------- |
| `channel.kind`              | enum   | `slack`, `telegram`, `voice`, `imessage`, `cron`, `cli`           |
| `channel.workspace_or_chat` | string | Slack workspace, Telegram chat ID, etc. (hashed if PII-sensitive) |
| `channel.user_hash`         | string | sha256 of inbound user ID — never log raw user IDs                |
| `latency.ms`                | int    | For outbound: render-to-deliver wall clock                        |

## Optional attributes (recommended but not contract-enforced)

- `pf_runtime.skill_slug` for spans inside a skill execution (matches `~/.hermes/skills/{slug}` or `~/.claude/agents/{slug}`).
- `pf_runtime.parent_span_id` when explicitly nesting beyond what OTel spans carry by default.
- `business.outcome` for spans that map to a profile-level OKR (e.g. `lead_qualified`, `proposal_drafted`) — used by the atlas-ceo weekly roll-up.

## Forbidden in spans

These never appear, even if a tool would let them:

- Raw user message content (PII risk; use `pf_runtime.session_id` to join back to `state.db.messages` if needed for debugging — and only with operator approval).
- Raw API keys, OAuth tokens, signed approval tokens.
- Skill-self-gen code output (auto-authored skill source goes in `mutation_audit` per `SKILL_SELF_GEN_BOUNDS.md`, never in the trace stream).

## Hermes-side adapter (G1 baseline window)

Hermes does not emit OTel spans natively at v0.12.0. The G1 capture script wraps every `state.db.sessions` row + corresponding `messages` rows into a synthetic span set conforming to this schema before writing to `HERMES_BASELINE.md`. Mapping:

| Schema attr                 | Hermes column                                                                            |
| --------------------------- | ---------------------------------------------------------------------------------------- |
| `pf_runtime.profile_slug`   | active profile when row was written                                                      |
| `pf_runtime.session_id`     | `sessions.id`                                                                            |
| `pf_runtime.runtime`        | `hermes-` + `hermes --version` output                                                    |
| `pf_runtime.runtime_commit` | `git -C ~/.hermes/hermes-agent rev-parse --short HEAD` (set per-night by capture script) |
| `pf_runtime.span_kind`      | `loop_iteration` (sessions row) + `llm_call` per `messages.role='assistant'` row         |
| `llm.provider`              | `sessions.billing_provider`                                                              |
| `llm.model`                 | `sessions.model`                                                                         |
| `tokens.input/output`       | `sessions.input_tokens / output_tokens`                                                  |
| `tokens.cache_read/write`   | `sessions.cache_read_tokens / cache_write_tokens`                                        |
| `cost.usd_estimated`        | `sessions.estimated_cost_usd`                                                            |
| `cost.usd_actual`           | `sessions.actual_cost_usd`                                                               |
| `latency.ms`                | `(ended_at - started_at) * 1000`                                                         |

This wrapping happens in `scripts/g1-baseline-capture.sh` (per plan §6.A) — do not duplicate the logic in PF Runtime once Hermes is retired.

## Versioning + reversibility

- `pf_runtime.schema_version` starts at `1`. Bump on any non-additive change (column rename, column removal, type change). Additions are version-compatible.
- The contract test runs in CI; it loads a frozen fixture span at version 1 and asserts the validator accepts it. Bumping the version requires a corresponding fixture file at the new version + an explicit migration note here.
- Old version traces are archived per ADR-006's 90-day forensic window — never deleted while still in window.

## Contract test (`tests/trace_schema_contract.py`)

The test asserts every span emitted during a `g1-baseline-capture.sh` dry run validates against the JSON Schema generated from this doc. The schema is the table above mechanically converted; the test fails if any required attribute is missing OR if any forbidden attribute is present (heuristic match on attribute name).

Test fixture: `tests/fixtures/trace_schema_v1_valid.json` and `tests/fixtures/trace_schema_v1_invalid.json`.

## What this doc explicitly does NOT cover

- OTel span context propagation across A2A peer boundaries — that's an A2A concern, lives in the A2A spec.
- Langfuse-specific trace metadata (e.g. `langfuse.session_id` vs `pf_runtime.session_id`) — Langfuse adapter MUST translate schema attrs into Langfuse's own attrs at egress; not the reverse.
- Per-skill custom attributes — skills MAY emit additional attrs prefixed with `skill.<slug>.<name>`; those don't go through this contract.
