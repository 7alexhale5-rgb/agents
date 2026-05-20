---
date: 2026-05-20
type: decision
status: active
tags: [capability, autonomy, roadmap, hermes-pin, karpathy-ladder]
roadmap: /Users/alexhale/Projects/agents/docs/capability-roadmap.md
plan: /Users/alexhale/.claude/plans/get-everything-fully-up-fancy-steele.md
supersedes: none
related_adrs:
  - 2026-05-04-adopt-hermes.md (ADR-001 — pin v0.12.0)
  - 2026-05-18-hermes-pfos-event-contract.md (patch #5 emitter)
---

# Capability Build Sequence + Pin Doctrine — Phase 3 decision

## Context

The capability roadmap at `docs/capability-roadmap.md` enumerates 18 candidate capability moves across three tiers (match Jack, exceed Jack, lap the field) ranked into a queue of 8 top items. This doc commits to the first three waves, names their gates, and locks the v0.12/v0.13/v0.14 pin doctrine.

The "we don't compete with Jack" framing in earlier docs was wrong for Lane 2 (`@alexdoesai`). Agent capability is upstream of both lanes — the agents need to be excellent regardless. This sequence builds toward parity with Jack on the autonomous-workflow surface AND exceedance on the governance + interoperability surface that nobody in the community has shipped.

## Decision

### Wave 1 — ship this week (no dependencies, ~5 hours total)

Three items, all parallel-shippable, all in v0.12 native (no runtime bump). Land the foundation before the heavy work.

**1. Enable Autonomous Curator on 7-day cron** (Tier 2, ~1h)

The Curator is a background agent already shipped in v0.12 that prunes + consolidates skills weekly. Per-run reports at `~/.hermes/logs/curator/run.json` + `REPORT.md`. `hermes curator status` ranks skills by usage. Nobody in Jack's demos runs this. The 27 PrettyFly skills will benefit from automated dead-code pruning as the fleet grows.

**Effort:** Config-only — add `auxiliary.curator` model to `~/.hermes/config.yaml` + enable the curator block.

**Gate:** After first scheduled fire (~7 days), `~/.hermes/logs/curator/run.json` exists. `hermes curator status` ranks ≥3 skills by usage. Zero skill deletions in the first run (the report is the artifact, not the action — Karpathy throwaway-version-first).

**2. Wire `/goal` Ralph loop into atlas-ceo's weekly-ceo-operating-loop skill** (Tier 1, ~2h)

`/goal` is already in v0.12 (`hermes_cli/goals.py`). Locks the agent on objective across turns with an auxiliary judge call between turns and a turn-budget backstop. Jack's autopilot demos use this primitive. atlas-ceo's weekly-ceo-operating-loop currently fires as a single turn — adding `/goal` lets it iterate on its own brief until the judge passes.

**Effort:** Update the skill prose at `hermes/profiles/atlas-ceo/skills/weekly-ceo-operating-loop.md` to invoke `/goal` with the brief acceptance criteria as the objective. Smoke-test against a fixture.

**Gate:** One atlas-ceo weekly-ceo-operating-loop completes via `/goal` with auxiliary judge progress events visible in `public.agent_events` (look for events with `data.goal_iteration` populated). End-to-end <5 minutes.

**3. Install `stainlu/hermes-labyrinth` observability dashboard** (Tier 2, ~2h)

Read-only observability — Journey/Crossing/Inspector/Skill-Atlas/Cron-Gate/Model-Ferry views with auto-redaction. Read-only-by-design matches the propose-only doctrine. Layered on top of the existing Langfuse path. 272 stars, MIT. Single biggest UX upgrade for any human reviewer touching agent output.

**Effort:** `hermes skills install https://github.com/stainlu/hermes-labyrinth` + per-profile config to enable Labyrinth instrumentation hooks. Smoke against one Atlas weekly brief session.

**Gate:** Labyrinth UI renders ≥1 PrettyFly session journey with all crossings labeled (prompts, tool calls, results, failures, model switches, cron runs). Redaction passes on any `SLACK_BOT_TOKEN` / `HERMES_AGENT_EVENTS_TOKEN` substrings in the traced session.

### Wave 2 — week 2 (depends on Wave 1 stable, ~14 hours total)

Two heavier items that build on the Wave-1 foundation.

**4. OMH `ralplan` consensus pattern for marin → quill → stet** (Tier 2, ~6h)

Adopt `witt3rd/oh-my-hermes` Planner-Architect-Critic debate skill followed by verify-iterate executor. Marin proposes the decision (Planner role), Quill drafts (Architect), Stet critiques (Critic), consensus event emitted with `parent_run_id` chain. MIT, shippable as `hermes skills install`. Replaces the current independent-propose-into-`_inbox/` shape with structured multi-agent coordination.

**Effort:** Install OMH skills, rewrite marin/quill/stet skill prose to invoke ralplan rather than emit independently, eval-gate the new shape against 4 fixtures.

**Gate:** One end-to-end run: marin proposes weekly decision → quill drafts the readout → stet critiques → consensus event emitted to `public.agent_events` with `parent_run_id` linking all three. Visible in Labyrinth's Journey view as a single multi-agent crossing.

**Depends on:** Wave 1 item 3 (Labyrinth, so we can trace the chain).

**5. PFOS-aware approval-instrumentation plugin** (Tier 3, ~8h)

v0.12 ships `pre_gateway_dispatch` / `pre_approval_request` / `post_approval_response` plugin hooks. Nobody in the ecosystem has built audit-grade approval instrumentation. Build a plugin that intercepts every approval flow (Slack emoji, Block Kit, future ACP) and writes a structured `approval_decision` event to `public.agent_events` regardless of source. Unifies the inbox view at `os.prettyflyforai.com/agents/inbox`.

**Effort:** Plugin scaffold + 3 hooks + write-back to PFOS via existing `/api/silos/<slug>/agent-event` endpoint. Test against both Slack paths (live emoji + dormant Block Kit when scopes land).

**Gate:** Every approval (Slack emoji + Block Kit + manual SQL flip) writes an `approval_decision` event with `approver`, `decided_event_id`, `decision`, `surface`. `/agents/inbox` shows unified approval history.

### Wave 3 — week 3-4 (post-30-day gate, ~8 hours total)

Two items including the runtime bump. Triggered when Wave 1 + Wave 2 have run cleanly for 14+ days and the Phase-4 Karpathy gate clears.

**6. Land `Rainhoole/hermes-agent-acp-skill` + ACP-spec the existing `a2a-card.json` files** (Tier 3, ~4h)

Highest-leverage strategic move. Makes PrettyFly's profiles interoperable with the wider Hermes community on a converging standard (32 stars on the ACP skill, Composio shipping Discord MCP for Hermes, v0.14 upstream channel-skill-bindings). Profiles become discoverable, callable agents in any Hermes fleet — without surrendering the propose-only authority + contract-first PFOS approval surface that's the actual differentiation.

**Effort:** Install ACP skill + audit each profile's `a2a-card.json` against the ACP schema + add ACP routing block to each `config.yaml`.

**Gate:** An external Hermes session running `delegate_task` with ACP routing can reach atlas-ceo and receive a contract-shaped response. PFOS approval surface still mediates the response per propose-only doctrine.

**Depends on:** Wave 2 item 5 (Approval plugin, so cross-fleet calls get instrumented).

**7. Runtime bump v0.12 → v0.13 "Tenacity"** (mixed, ~3h)

Adopt the kanban zombie reclaim + Checkpoints v2 + post-write delta linting + session auto-resume. Skips v0.14 for now (defer to day-60).

**Pre-flight (mandatory):**

1. Set `redaction.enabled: false` in `~/.hermes/config.yaml`. v0.13 flips this default ON; the Quill drafts pipeline relies on off — without this step the pipeline starts mangling tool outputs.
2. Snapshot `~/.hermes/checkpoints/` (Checkpoints v2 migration is one-way). `cp -R ~/.hermes/checkpoints ~/.hermes/checkpoints.v0.12.bak`
3. Audit any custom model-provider plugins for the `plugins/model-providers/` path move. PrettyFly currently has none, but confirm.
4. `scripts/sync-profile.sh pull` all 5 profiles before bump; `scripts/sync-profile.sh push` after; confirm no shape drift.

**Bump:**

```bash
hermes update
hermes doctor
```

**Gate:** All 4 live profiles emit one event each post-bump within 24h. No malformed YAML in `_inbox/quill-drafts/` or `_inbox/stet-critiques/`. Checkpoints survived migration (`hermes checkpoint list` returns ≥1 row that existed pre-bump).

**8. Adopt `no_agent: true` for `verify-event-contract` + Atlas heartbeat crons** (Tier 1, ~1h)

Two crons today spin a full agent and emit one structured event. v0.13's `no_agent` mode bypasses the entire agent layer — script runs, stdout delivers verbatim, zero LLM token cost.

**Effort:** Per-job flag in cron config for `verify-event-contract.py` and Atlas heartbeat.

**Gate:** Both crons run with zero LLM token spend (verify via Langfuse). Verifier still catches contract violations (inject a test violation, confirm it surfaces). Atlas heartbeat still updates last-seen.

**Depends on:** Item 7 (v0.13).

## Pin doctrine (locked)

- **Stay at v0.12.0 for ~30 days (until ~2026-06-20).** Items 1-5 ship without a runtime bump. Phase 4 just landed (`a068a24`, 2026-05-19) and its Karpathy gate is "4 weeks of scheduled emissions, zero ADR violations." Bumping resets the gate.
- **Bump to v0.13.0 at day-30 gate clearance, NOT v0.14.** `no_agent` mode is the single highest-impact change for the cron-driven fleet. Pre-flight per Wave 3 item 7.
- **Defer v0.14 until day-60 gate clears (~2026-07-20).** Cross-session prompt caching is automatic when present; deferring costs marginal tokens, not capability. OpenAI-compatible local proxy is interesting for the codex profile but Phase 5.5 (codex rebuild) is gated behind Phase 5 (koho-ops + yeh-ops).

**Override clause:** if upstream ships a security CVE patch in v0.13 or v0.14 before the day-30 / day-60 gates, bump immediately regardless of the gate. Reset the Karpathy timer and document the override in a new ADR.

## Out of scope this sequence

Items deliberately deferred — name + reason so future sessions don't re-add them:

- **v0.14 bump** — day-60 gate, see above.
- **Codex profile rebuild** — Phase 5.5 in $1M plan, gated behind Phase 5.
- **LINE / SimpleX gateways** — zero revenue surface for PrettyFly (no JP/KR/TW ICP, no privacy-decentralized buyer persona).
- **Memory backend swap** (Mnemosyne / mnemo-hermes / flowstate-qmd / yantrikdb / plur) — `honcho.enabled: false` everywhere today. Bring up only if a profile hits a memory wall built-in FTS5 can't handle.
- **`builderz-labs/mission-control` adoption** — namespace-collides with PrettyFly's retired Mission Control. PFOS approval surface is the equivalent.
- **Trust/payment guardrails** (`nativ3ai/hermes-agent-camel`, `hermes-payguard`) — closest analogues to PrettyFly's propose-only doctrine, but PrettyFly already implements the same intent via contract-first tool boundaries. Revisit only if x402 micropayments become a revenue surface.
- **Multi-profile orchestration with explicit handoff contracts** — partial via item 4 (OMH ralplan). Full implementation deferred until ralplan stabilizes.
- **`hermes-incident-commander` pattern** — Phase 5 (koho-ops / yeh-ops) work, not this sequence.

## Verification end-to-end

After Wave 1 + Wave 2 ship: Alex can walk the live agent on `os.prettyflyforai.com/agents` and observe:

- Atlas weekly-ceo-brief running via `/goal` with iteration events visible in the Live event tail
- Curator weekly report visible in `~/.hermes/logs/curator/`
- Labyrinth journey view showing the marin → quill → stet ralplan chain
- `/agents/inbox` rendering unified approval history across emoji + Block Kit + manual paths
- `parent_run_id` linkage visible on at least one multi-profile event chain

After Wave 3 ships: same surfaces, plus an external ACP `delegate_task` call hitting atlas-ceo, plus zero-LLM-cost cron runs for verify-event-contract + Atlas heartbeat.

## Related

- Plan: `~/.claude/plans/get-everything-fully-up-fancy-steele.md`
- Roadmap: `/Users/alexhale/Projects/agents/docs/capability-roadmap.md`
- ADR-001 (the pin): `_meta/decisions/2026-05-04-adopt-hermes.md`
- Event contract: `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`
- Positioning doctrine: `~/Projects/marketing/decisions/2026-05-20-hermes-positioning-truth.md`
- Truth audit swarm: `~/Projects/marketing/_inbox/2026-05-20-hermes-truth-audit/`
- Community index: `github.com/0xNyk/awesome-hermes-agent`
