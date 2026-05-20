# Hermes Capability Roadmap — match-or-exceed the field

> **Date:** 2026-05-20 (afternoon)
> **Plan:** `~/.claude/plans/get-everything-fully-up-fancy-steele.md` (Phase 2 deliverable)
> **Trigger:** Alex pushed back on the prior "differentiate by avoiding Jack's lane" framing. `@alexdoesai` IS Jack's lane; the right posture is match-or-exceed. Agent capability is upstream of both lanes and needs to be excellent regardless.
> **Inputs:** 3-agent research swarm landed 2026-05-20: PrettyFly capability audit (Phase 1A), v0.12→v0.14 Hermes delta (Phase 1B), community ecosystem survey (Phase 1C / 126+ projects in `0xNyk/awesome-hermes-agent`).

## TL;DR

PrettyFly's Hermes stack is on-spec for the upstream `delegate_task` orchestrator pattern + the proposed `agent_profiles` evolution (issue #9459). The doctrine layer — propose-only, contract-first, fcntl-locked rate caps, agent_events emitter — is genuine IP nobody else has shipped. **But the runtime is two minor versions behind, the curator/self-improvement loop is dormant, and four community projects have shipped patterns we should adopt directly: OMH consensus-planning, Labyrinth observability, ACP cross-agent routing, incident-commander autonomous SRE.** The match-Jack work is mostly wiring features Hermes already ships. The exceed-Jack work is layering ACP-compatible routing on top of our existing PFOS approval surface so PrettyFly profiles become discoverable agents in any Hermes fleet without surrendering governance.

Three corrections to prior framing land in this doc:

1. "Pantheon" + "council" + "14 personalities" in earlier docs were research-vault speculation, not shipped Hermes terms. The actual primitive is `delegate_task` (v0.11+). `agent_profiles` is the upstream proposal at issue #9459, still open. PrettyFly is on-spec for both.
2. `/goal` Ralph loop, `hermes -z` one-shot, `wakeAgent` cron gate, Curator background agent, plugin hooks (`pre_gateway_dispatch`, `pre_approval_request`, `post_approval_response`) are all in v0.12 already and unused by the PrettyFly fleet.
3. `@alexdoesai` (Lane 2 creator-content) IS Jack Roberts' lane — same audience, head-on competition the right posture. Lane 1 (PrettyFly Advisory / WORKS Review) is different.

## Section 1 — Current state

### Per-profile inventory

| Profile       | Rung | Skills                                                                                                                                                      | Tools (contract-bound)                                                                                                                                            | Channels              | Event types                                                                | Daily cap | Phase status                                                                                                                                       |
| ------------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | -------------------------------------------------------------------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **atlas-ceo** | 3    | 8 (weekly-ceo-brief, weekly-ceo-operating-loop, decision-memo, source-packet-triage, business-scorecard-brief, approval-proposal-draft, self-audit, README) | 4 (`fleet.snapshot` read-only, `business.scorecard.snapshot` read-only, `atlas.propose_action` proposed_write_only, `atlas.record_follow_up` evidence_write_only) | Slack DM only         | `atlas.action.proposed` (pending) · `atlas.follow_up.recorded` (completed) | 3/day     | Live. Blind interview 9/9, PFOS approval+follow-up loop passing, premium Sonnet route confirmed                                                    |
| **marin**     | 2    | 7 (weekly-review, buyer-signal-router, supervised-dispatch, campaign-brief-draft, kill-list-enforce, self-audit, README)                                    | 4 (`marketing_vault.read`, `message_ledger.read`, `scoreboard.read`, `weekly_decision.propose`)                                                                   | None (Slack disabled) | `marin.weekly_decision.proposed` (pending)                                 | 1/day     | Phase 2 product gate passed (AI Ops Audit weekly readout accepted by Alex). Buyer-signal-router cleared synthetic gate, waiting on real route-open |
| **quill**     | 2    | 6 (draft-linkedin-field-note, draft-outreach-message, draft-campaign-asset, revise-from-critique, self-audit, README)                                       | 5 (`marketing_vault.read`, 4× `draft_*.propose` to `_inbox/quill-drafts/`)                                                                                        | None                  | `quill.draft.proposed` (4 skill_slugs via per-tool event blocks)           | 5/day     | Scaffolded 2026-05-20. Lint PASS, eval seeded. Gate: one real draft + matching agent_events row                                                    |
| **stet**      | 2    | 6 (critique-draft, critique-campaign-brief, critique-positioning, pressure-test-campaign, self-audit, README)                                               | 6 (`marketing_vault.read`, `draft_inbox.read`, 4× `critique_*.propose` to `_inbox/stet-critiques/`)                                                               | None                  | `stet.critique.proposed` (4 skill_slugs)                                   | 2/day     | Scaffolded 2026-05-20. Lint PASS. Gate identical to quill                                                                                          |
| **codex**     | —    | 0 (only `.gitkeep`)                                                                                                                                         | none                                                                                                                                                              | none                  | none                                                                       | uncapped  | Placeholder. CLAUDE.md has `TBD` in tier/channels/phase/routing/model/gate. Phase 5.5 in $1M plan (3-5 hour rebuild from Atlas template)           |
| **ops**       | —    | none                                                                                                                                                        | none                                                                                                                                                              | none                  | none                                                                       | n/a       | Archived. Only `scratch/relay-errors.log` + `scratch/last-critical.txt` remain                                                                     |

### Doctrine layer (genuine PrettyFly IP)

- **agent_events emitter contract** — `hermes/lib/agent_events.py` (337 LOC). Reads `tools.contracts.<tool>.event` blocks, refuses to ship if missing required ADR fields (`agent_slug`, `type`, `status`, `surface`, `cwd_project`, `skill_slug`, `runtime`, `private_payload_redacted`). Bearer-authed POST to PFOS `/api/silos/<silo>/agent-event`. Source: `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`.
- **Propose-only authority model** — every write tool declares `proposed_write_only` or `evidence_write_only`. `proposals.execute: false` everywhere. Marin/Quill/Stet zero out `outbound_channels`; Atlas keeps `[slack]` for DM-only delivery.
- **Per-skill attribution pattern** — Quill ships 4 distinct `*.propose` tools that all emit `quill.draft.proposed` but carry different `skill_slug` values per the contract block. Same for Stet. One event type, multi-skill attribution, no emitter modifications.
- **fcntl-locked rate caps** — `fleet/limits.json`: atlas 3/day, marin 1/day, stet 2/day, quill 5/day, codex uncapped. Cap enforcement after payload build, before POST. `RateLimitExceeded` subclass carries `profile`, `limit`, `today` so skills can queue locally. `dry_run` bypasses counter.
- **Two-path Slack notify** — `hermes/lib/slack_notify.py` (270 LOC). Live emoji-reaction path (`notify_decision`) + dormant Block Kit interactive path (`notify_decision_block_kit` + `build_decision_blocks`). Both correlate via `event:<agent_event_id>` for write-back to the right row.
- **Karpathy-ladder posture** — atlas rung 3, marin/quill/stet rung 2. Falsifiable SQL gates against `public.agent_events`.
- **Source-grounding requirement** — every real output skill must call `marketing_vault.read` / `fleet.snapshot` / `business.scorecard.snapshot` before any claim. Cheap nemotron-3-nano route labeled smoke-only; production briefs use Sonnet; high-stakes uses Opus.

### Self-built tooling layer

- `hermes/lib/agent_events.py` — the emitter contract enforcer
- `hermes/lib/slack_notify.py` — the two-path Slack notifier
- 4d-senses MCP (custom MCP server, separate repo)
- LAIK substrate (separate repo)
- PFOS write-back endpoints (`/api/silos/<slug>/agent-event`, etc. — separate repo)
- `scripts/{wire-fleet-cron,check-autonomy-gates,emit-agent-event,verify-event-contract}.{sh,py}`

## Section 2 — Available-but-unused (v0.12 native gap)

These ship in PrettyFly's pinned v0.12 install today. Zero version bump required.

| Capability                                                                                  | What it enables                                                                                                                                                       | Adoption cost                                           |
| ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| **Autonomous Curator** (`hermes curator`)                                                   | Background agent prunes + consolidates skills on 7-day cron. Per-run reports at `logs/curator/run.json` + `REPORT.md`. `hermes curator status` ranks skills by usage. | Config: add `auxiliary.curator` model + enable          |
| **`/goal` Ralph loop**                                                                      | Locks agent on objective across turns; auxiliary judge call between turns; turn-budget backstop. Already in `hermes_cli/goals.py`.                                    | None — invoke directly                                  |
| **Self-improvement loop**                                                                   | Class-first rubric review fork after each turn; active-update bias; restricted to memory+skills toolsets.                                                             | Default-on, opt-out via config                          |
| **`hermes -z <prompt>` one-shot mode**                                                      | Non-interactive CLI invocation with `--model`/`--provider`. Ideal for cron jobs that need an answer without a session.                                                | Swap cron `script:` jobs for `hermes -z` calls          |
| **`wakeAgent` cron gate**                                                                   | Script returns `{"wakeAgent": false}` → skip LLM invocation entirely. Distinct from v0.13's `no_agent` (which bypasses agent boot).                                   | Add gate JSON to scripts                                |
| **`kanban_heartbeat` worker tool**                                                          | Callable from workers; gated on `HERMES_KANBAN_TASK` env. Already wired in `tools/kanban_tools.py:272-296`.                                                           | None                                                    |
| **Plugin hooks** (`pre_gateway_dispatch`, `pre_approval_request`, `post_approval_response`) | Plugin can intercept messages before agent dispatch / instrument approval flows.                                                                                      | Plugin code                                             |
| **`duration_ms` on `post_tool_call`**                                                       | Per-tool timing for observability.                                                                                                                                    | Plugin code                                             |
| **`prompt_caching.cache_ttl` 5m → 1h**                                                      | Cost savings for bursty sessions.                                                                                                                                     | Config flip                                             |
| **Skill install from URL** (`hermes skills install <url>`)                                  | Install any HTTP(S)-hosted skill.                                                                                                                                     | None                                                    |
| **`/reload-skills` slash command**                                                          | Hot-reload skill changes without restarting.                                                                                                                          | None                                                    |
| **`skill_manage` edits in `external_dirs`**                                                 | Worker agents can mutate user's skill bundles in place.                                                                                                               | None                                                    |
| **Vercel Sandbox `execute_code` backend**                                                   | Cloud sandboxed code execution.                                                                                                                                       | Provider config                                         |
| **Bundled Langfuse + hermes-achievements plugins**                                          | Observability + session history scan, both opt-in.                                                                                                                    | Plugin enable                                           |
| **Remote model catalog manifest**                                                           | New OpenRouter / Nous Portal models auto-appear without release.                                                                                                      | Default-on                                              |
| **`delegate_task` orchestrator pattern** (v0.11+, the actual Hermes subagent primitive)     | Single tool, orchestrator-role spawns subagents with `max_spawn_depth`. The shipped `agent_profiles` proposal at #9459 builds on this.                                | Config: declare orchestrator role + per-subagent config |

### v0.13.0 "Tenacity" (2026-05-07) — net new since the pin

| Capability                                                 | Enables                                                                                                                                                                                                                                  | Adoption cost                      |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **`no_agent: true` cron mode**                             | Per-job flag — script runs, stdout delivers verbatim, zero LLM token cost. Distinct from `wakeAgent` (which still pays agent-boot tax). For watchdog/heartbeat jobs.                                                                     | Runtime bump + per-job flag        |
| **Kanban zombie detection + reclaim**                      | Stalled workers auto-detected, reclaimed, retried per-task. Generic distress-signal engine treats spawn/timeout/crash equivalently.                                                                                                      | Runtime bump                       |
| **Checkpoints v2**                                         | Rewritten state persistence — real pruning, disk guardrails, no orphan shadow repos. **One-way migration; snapshot `~/.hermes/checkpoints/` before bump.**                                                                               | Runtime bump                       |
| **Post-write delta linting**                               | `write_file` + `patch` outputs validated against Python/JSON/YAML/TOML linters before reaching next turn. Catches Quill drafts that emit malformed YAML frontmatter.                                                                     | Runtime bump, default-on           |
| **Session auto-resume on gateway restart / source reload** | In-flight conversations survive `hermes update` or process restart.                                                                                                                                                                      | Runtime bump, default-on           |
| **Google Chat platform (20th)**                            | Native gateway adapter.                                                                                                                                                                                                                  | Runtime bump + per-platform config |
| **Pluggable model-provider plugins**                       | Custom providers ship as plugins; replaces in-core registration. Breaking for any custom-provider plugins.                                                                                                                               | Runtime bump (path migration)      |
| **8 P0 security closures**                                 | Includes **redaction default flipped back to ON** — reverses v0.12's default-off. Must explicitly set `redaction.enabled: false` in `~/.hermes/config.yaml` before bump or the Quill drafts pipeline starts mangling tool outputs again. | Runtime bump (with pre-flight)     |

### v0.14.0 "Foundation" (2026-05-16) — net new since v0.13

| Capability                                                                           | Enables                                                                                                                                                                                                           | Adoption cost                      |
| ------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- |
| **Cross-session Claude prompt caching (1h)**                                         | System prompt + skills + memory cache across separate session boots. Background memory-review also hits the cache. Direct cost reduction for the 5-profile roster.                                                | Runtime bump, automatic            |
| **Browser CDP persistent connection**                                                | ~180× faster `browser_*` tool calls.                                                                                                                                                                              | Runtime bump, transparent          |
| **OpenAI-compatible local proxy**                                                    | `http://localhost:<port>` endpoint speaks OpenAI API backed by OAuth providers (Claude Pro, ChatGPT Pro, SuperGrok). Codex CLI / Aider / Cline plug in without API keys. **Wedge for the codex profile rebuild.** | Runtime bump + proxy enable        |
| **Native X (Twitter) search tool**                                                   | First-class tool.                                                                                                                                                                                                 | Runtime bump + auth config         |
| **`/handoff` mid-session model switch**                                              | Moves live session to different model/persona/profile without restarting.                                                                                                                                         | Runtime bump                       |
| **LINE (21st) + SimpleX Chat (22nd) platforms**                                      | LINE for JP/KR/TW reach; SimpleX for privacy-decentralized.                                                                                                                                                       | Runtime bump + per-platform config |
| **`/sessions` browser/resumer**                                                      | UI for finding + resuming prior sessions.                                                                                                                                                                         | Runtime bump                       |
| **Approval events on API server**                                                    | Long-running runs no longer silently hang on approval-required commands.                                                                                                                                          | Runtime bump                       |
| **Cron `deliver=all`**                                                               | Fan-out cron result to every connected channel.                                                                                                                                                                   | Runtime bump + per-job config      |
| **Plugin `ctx.llm`**                                                                 | Plugins can issue arbitrary LLM calls without wiring their own client.                                                                                                                                            | Plugin API                         |
| **Kanban orchestrator tools** (`kanban_list`, `kanban_unblock`, `stranded_in_ready`) | Orchestrator agent can list board state and unstick stuck tasks.                                                                                                                                                  | Runtime bump                       |
| **`specify` — auxiliary LLM fleshes out triage tasks**                               | Triage worker uses aux model to expand thin task descriptions before assigning.                                                                                                                                   | Runtime bump + aux model config    |
| **~19s cold-start reduction**                                                        | Deferred adapter loading, parallel doctor, `hermes tools` All-Platforms ~14s → ~1.5s.                                                                                                                             | Runtime bump                       |

## Section 3 — Community enhancements (peer power-user gap)

The Hermes Agent ecosystem is much bigger than the prior truth audit captured: 126+ projects in `github.com/0xNyk/awesome-hermes-agent`. Below are the high-leverage patterns PrettyFly should benchmark against.

### Multi-agent orchestration

| Project                                  | Stars | Pattern                                                                                                                                                                                              |
| ---------------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`witt3rd/oh-my-hermes` (OMH)**         | 28    | Planner-Architect-Critic consensus-debate skill (`ralplan`) followed by verify-iterate executor (`ralph`). Chains research → interviewing → planning → execution. 8 named orchestration skills. MIT. |
| **`HERMESquant/oh-my-hermes` fork**      | 4     | Claude Code + Codex CLI unified handoff (`omh handoff codex` / `omh handoff claude`) with shared `.omh/` state. 28+ agent catalog. `dualforge`/`autopilot`/`ultrawork` magic keywords. MIT.          |
| **`Rainhoole/hermes-agent-acp-skill`**   | 32    | Agent Communication Protocol skill — standardized `agent=...` routing across Hermes subagents, Codex, Claude Code. Context isolation + timeout/output safety controls. MIT.                          |
| **`Lethe044/hermes-incident-commander`** | 30    | Autonomous SRE loop: 5-min health checks + hourly audits + P0-P3 triage + tiered remediation + post-incident skill writing. Detect→triage→diagnose→remediate→verify→learn. MIT.                      |

### Observability + dashboards

| Project                             | Stars | Pattern                                                                                                                                                                                                                                                                                                                            |
| ----------------------------------- | ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`stainlu/hermes-labyrinth`**      | 272   | Read-only observability dashboard. Journey/Crossing/Inspector/Skill-Atlas/Cron-Gate/Model-Ferry views. Auto-redaction. Read-only-by-design enforced as constraint. MIT v0.1.3.                                                                                                                                                     |
| **`builderz-labs/mission-control`** | 4,900 | 32-panel self-hosted dashboard. RBAC (viewer/operator/admin), WebSocket+SSE real-time, multi-agent orchestration with quality-review gates + Kanban, adapter layer for OpenClaw/CrewAI/LangGraph/AutoGen/Claude SDK. **Namespace collides with PrettyFly's retired Mission Control — different codebase, but flag for marketing.** |
| **`EKKOLearnAI/hermes-web-ui`**     | 5,600 | Vue 3 dashboard. Session-and-analytics-managed with multi-agent chat panel.                                                                                                                                                                                                                                                        |
| **`luoyuctl/agenttrace`**           | —     | Lightweight local TUI for session cost/token/failure audits. Complement to Langfuse.                                                                                                                                                                                                                                               |

### Memory backends (alternatives to Honcho)

`AxDSan/Mnemosyne` (sub-ms local), `eleion-ai/mnemo-hermes` (pgvector), `amanning3390/flowstate-qmd` (anticipatory RAG), `yantrikos/yantrikdb` (conflict-detection memory), `plur-ai/plur` (shared engram format). Four competing durable-memory backends directly address PrettyFly's `honcho.enabled: false` gap.

### Trust / payment guardrails

`nativ3ai/hermes-agent-camel` (CaMeL trust boundaries) + `nativ3ai/hermes-payguard` (USDC/x402 spending limits). Closest community analogues to PrettyFly's contract-first propose-only governance.

### Enterprise-shaped deployments

`jasperan/orahermes-agent` — Oracle AI Agent Harness over OCI GenAI + Oracle 26ai. Proof Hermes can land in enterprise procurement.

`HermesOS.cloud` (Nous-operated) — $0 / $9.99 / $19.99 hosted tiers. Telegram/Discord/Slack/WhatsApp out of the box. "Hive Mind" network-wide learning roadmap. **No customer logos or case studies on the public site — enterprise traction claims not yet evidence-backed.**

### Peer creators on YouTube (Lane 2 benchmark set)

- **Nate Herk** (`@nateherk`) — "Hermes Agent: Zero to Personal AI Assistant (1 Hour Course)" + competed against Jack in "$10K AI Agent Gameshow" (Agentic Arena). Different positioning (business-automation, not Jack's superlative-bait).
- **Julian Goldie** (Goldie Agency, 70K subs) — "Hermes Agent Workspace: The Complete 2026 Guide" + SEO-optimized written guides at `juliangoldie.com`. Owns the search-intent surface Jack doesn't.
- **Spanish-language channels** — "NUEVO Hermes Agent Curso COMPLETO" (1 week old). International audience PrettyFly has zero presence in.

### Reference indexes

- **`0xNyk/awesome-hermes-agent`** — canonical 126+ entry community index. Monthly read.
- **`OnlyTerp/hermes-optimization-guide`** — 24-part working-artifact guide (skill templates, configs, VPS bootstrap, Docker Compose). v0.13.0-tracked. Most concrete deployment recipe in the ecosystem.
- **`@0xmega` Medium guide** — Hermes Agent VPS deployment (Telegram + Discord + VPS, no Mac Mini). Closes the macOS-dependence gap PrettyFly's stack inherited.

## Section 4 — Match-or-exceed roadmap

### Tier 1 — Match Jack (and the broader YouTube cohort)

Capabilities Jack demonstrates publicly that PrettyFly profiles should be able to do at parity:

1. **Cron-driven autonomous loops** that emit visible work product. Jack's demos run cron jobs that produce drafts, emails, summaries continuously. PrettyFly's cron infrastructure exists (Phase 4 landed 2026-05-19) but four of five profiles still execute on-demand only. **Adopt:** `hermes -z` one-shot mode (v0.12 already) for every profile's `self-audit` skill; wire `wakeAgent` cron gates to skip unnecessary LLM calls.
2. **Telegram dispatch** as the visible operator surface. Currently atlas-ceo is Slack DM only; marin/quill/stet have no channels. Jack's demos run on Telegram. **Adopt:** Telegram gateway (already in v0.12; 18 native channels) for at least atlas-ceo as a secondary channel. Composio's Discord MCP integration is a parallel option.
3. **Same-day reaction-skill drops** when upstream ships a new capability. Jack publishes within 24-48 hours of every Anthropic/Hermes release. **Adopt:** ship a "release-reaction" workflow — `codex` (when rebuilt) drafts a reaction artifact for every Hermes/Anthropic release. Lane-2 content output gets the Lane-1 governance.
4. **Visible blueprint catalog**. Jack ships 110+ blueprints to Skool. PrettyFly has skills internally but no externally-visible catalog. **Adopt:** publish a public-facing skill catalog (the 27 existing skills) — README per skill, agentskills.io conformance, install instructions.
5. **`/goal` Ralph loop** — Jack's autopilot demos use this primitive. Already in v0.12. **Adopt:** wire `/goal` into at least atlas-ceo's `weekly-ceo-operating-loop` skill.

### Tier 2 — Exceed Jack (doctrine + tooling layer he doesn't have)

Capabilities our doctrine layer enables that no Jack-style demo has shipped:

6. **OMH consensus-planning loop for the marin → quill → stet trio.** Today they propose into `_inbox/` independently. The OMH `ralplan` debate cycle (Planner-Architect-Critic → consensus plan → verified executor) is MIT and shippable as a `hermes/skills/` install. Folding it in earns Phase-3 → Phase-4 ladder progress without inventing the orchestration shape. **First gate:** Phase 2 CMO/Marin weekly-decision pilot.
7. **Hermes-labyrinth observability dashboard on top of Langfuse.** Current trace shape is `trajectory_jsonl + langfuse_project: hermes-<profile>` — production-correct but missing the journey/crossing/skill-atlas view. Labyrinth is MIT, 272 stars, read-only-by-design (matches propose-only doctrine). Single biggest UX upgrade for any human reviewer touching agent output.
8. **PFOS approval surface with audit trail** (already shipped via patch #5 emitter contract + `/agents/inbox`). This is what Jack doesn't have. Document it visibly so the differentiation is legible.
9. **Contract-first tool boundaries verifiable per profile.** Already shipped via `tools.contracts.<tool>.event` + `verify-event-contract.py`. Document it.
10. **fcntl-locked rate caps as governance feature.** Already shipped. Document.
11. **`/agents/inbox` HITL queue.** Already shipped. The 4d-senses + LAIK + PFOS combo is the visible governance product.
12. **Autonomous Curator** (v0.12 native, dormant). Background skill consolidation on 7-day cron. Nobody in Jack's demos runs this. **Adopt:** enable for the 27-skill catalog now; lets the fleet prune its own dead code.
13. **Cross-session prompt caching** (v0.14). Direct cost reduction for the 5-profile cron-driven roster. Jack hasn't talked about it because his demos don't run profile-by-profile.

### Tier 3 — Lap the field (build what upstream + community don't have)

14. **Land `Rainhoole/hermes-agent-acp-skill` + promote PFOS event-contract bindings to ACP-spec compatibility.** Highest-leverage strategic move. Makes PrettyFly's `a2a-card.json` shape interoperable with the wider Hermes community on a converging standard (32 stars on ACP skill, Composio shipping Discord MCP, v0.14 channel-skill-bindings upstream). PrettyFly profiles become discoverable, callable agents in any Hermes fleet without surrendering governance.
15. **Multi-profile orchestration with explicit handoff contracts.** atlas-ceo delegates to marin (weekly decisions) → marin delegates to quill (drafts) → quill delegates to stet (critique). The `delegate_task` primitive is in v0.12 today. **Build:** a `handoff_contract` schema in `_meta/decisions/` defining the allowed delegation graph + which events fire on each handoff. Wire via existing emitter contract.
16. **Agent-event-driven workflow chaining.** Already partially built via patch #5 (`agent_events` with `parent_run_id` field). **Extend:** PFOS reads agent_events and fires downstream profiles based on the event type. E.g., atlas-ceo emits `atlas.action.proposed` → PFOS dispatches marin to weigh in on marketing implications. The chain is recorded in `parent_run_id`.
17. **`hermes-incident-commander` pattern for koho-ops / yeh-ops** (Phase 5 in $1M plan, future). Lethe044's autonomous SRE loop is the closest community analogue to the autonomy ladder PrettyFly is building toward. Pattern: detect → triage → diagnose → remediate → verify → learn, with auto-skill-authoring on resolution.
18. **Plugin-based extension layer**. v0.12 ships `pre_gateway_dispatch` / `pre_approval_request` / `post_approval_response` plugin hooks. Nobody in the ecosystem has built audit-grade approval instrumentation plugins. **Build:** PFOS-aware plugin that intercepts every approval flow and writes a structured `approval_decision` event regardless of which channel the approval came from.

## Section 5 — Prioritized queue (impact × effort)

Top 8 ordered by leverage. Each gets a Karpathy gate (one measurable outcome, end-to-end).

| Rank | Capability                                                                                 | Tier  | Effort                                                                                                                    | Gate                                                                                                                                        | Dependency                                              |
| ---- | ------------------------------------------------------------------------------------------ | ----- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| 1    | **Enable Autonomous Curator on 7-day cron**                                                | T2    | <1h (config only)                                                                                                         | `~/.hermes/logs/curator/run.json` exists after first scheduled fire; ≥1 skill ranked by usage in `hermes curator status`                    | None                                                    |
| 2    | **Wire `/goal` Ralph loop into atlas-ceo weekly-ceo-operating-loop**                       | T1    | ~2h (skill prose update + smoke test)                                                                                     | Atlas weekly-ceo-brief completes with `/goal`-tracked progress events visible in agent_events                                               | None                                                    |
| 3    | **Install `stainlu/hermes-labyrinth` observability dashboard**                             | T2    | ~2h (`hermes skills install` + config)                                                                                    | Labyrinth UI renders ≥1 PrettyFly session journey with all crossings labeled                                                                | None                                                    |
| 4    | **Adopt OMH `ralplan` consensus pattern for marin → quill → stet**                         | T2    | ~6h (install + skill rewrites + eval gate)                                                                                | One end-to-end run: marin proposes decision → quill drafts → stet critiques → final consensus event emitted with `parent_run_id` chain      | Curator + Labyrinth (so we can trace the chain)         |
| 5    | **Build PFOS-aware approval-instrumentation plugin**                                       | T3    | ~8h (plugin scaffold + 3 hooks + PFOS endpoint)                                                                           | Every approval (Slack emoji + Block Kit + future) writes a structured `approval_decision` event; PFOS `/agents/inbox` shows unified history | None                                                    |
| 6    | **Land Rainhoole/hermes-agent-acp-skill + ACP-spec the existing `a2a-card.json`s**         | T3    | ~4h (skill install + per-profile a2a-card audit + ACP conformance)                                                        | An external Hermes session can `delegate_task` to atlas-ceo using ACP routing and receive a contract-shaped response                        | Approval plugin (so cross-fleet calls get instrumented) |
| 7    | **Runtime bump v0.12 → v0.13 "Tenacity"**                                                  | mixed | ~3h (pre-flight: snapshot checkpoints, set `redaction.enabled: false`, audit custom plugins, sync profiles; bump; verify) | All 4 live profiles emit one event each post-bump; no malformed YAML in `_inbox/`; checkpoints survived migration                           | Items 1-3 stable for ≥7 days first                      |
| 8    | **Adopt `no_agent: true` for `verify-event-contract` + Atlas heartbeat crons** (post-bump) | T1    | ~1h                                                                                                                       | Both crons run with zero LLM token spend; verifier still catches contract violations; Atlas heartbeat still updates last-seen               | Item 7 (requires v0.13)                                 |

### Deferred (don't ship until specific trigger)

- **v0.14 bump** — defer until day-60 gate clears (≈2026-07-20). Cross-session caching is automatic when present; deferring 60 days costs marginal token spend, not capability. OpenAI-compatible local proxy is interesting for codex but Phase 5.5 (codex rebuild) is gated behind Phase 5 (koho-ops + yeh-ops).
- **Codex profile rebuild** — Phase 5.5 in $1M plan. 3-5 hours of work. Defer until v0.14 bump lands so we can use the OpenAI-proxy wedge.
- **LINE / SimpleX gateways** — zero revenue surface for PrettyFly (no JP/KR/TW ICP; no privacy-decentralized buyer persona).
- **Memory backend swap** — `honcho.enabled: false` everywhere today; bring up only if a profile hits a memory wall that built-in FTS5 can't handle.
- **`builderz-labs/mission-control` adoption** — namespace-collides with PrettyFly's retired Mission Control. Don't adopt; the PFOS approval surface is the equivalent.

## Pin decision

**Stay at v0.12.0 for ~30 days (until ~2026-06-20).** Reasons:

- Phase 4 just landed (`a068a24`, 2026-05-19). Karpathy gate is "4 weeks of scheduled emissions, zero ADR violations." Bumping resets the gate.
- 80% of the autonomy-ladder day-30 + day-60 capabilities are already in the v0.12 install. Items 1-5 in the queue ship without a bump.
- v0.14 is 4 days old. Cross-session caching specifically has failure modes (cache poisoning, cross-profile context bleed) that take weeks to surface.

**Bump to v0.13.0 at day-30 gate clearance**, NOT v0.14. Pre-flight:

1. Set `redaction.enabled: false` in `~/.hermes/config.yaml` (v0.13 flips this default ON; Quill pipeline relies on off)
2. Snapshot `~/.hermes/checkpoints/` (Checkpoints v2 migration is one-way)
3. Audit any custom model-provider plugins for the `plugins/model-providers/` path move
4. Run `scripts/sync-profile.sh pull` on all 5 profiles; bump; `push` after to confirm no shape drift

**Defer v0.14 until day-60 gate clears (~2026-07-20).** Re-evaluate when codex profile rebuild starts.

## Verification

This roadmap is complete when Alex can answer all six in under 10 minutes of reading:

1. **What can our agents do today?** → Section 1
2. **What can they NOT do that upstream Hermes can?** → Section 2
3. **What can they NOT do that the community has shipped?** → Section 3
4. **What would we need to ship to match Jack?** → Section 4 Tier 1
5. **What would we need to ship to exceed him?** → Section 4 Tier 2 + Tier 3
6. **Which capabilities are worth shipping first?** → Section 5 (top 8 ranked by leverage)

## Related

- Plan: `~/.claude/plans/get-everything-fully-up-fancy-steele.md`
- Positioning doctrine (corrected): `~/Projects/marketing/decisions/2026-05-20-hermes-positioning-truth.md`
- Truth audit swarm: `~/Projects/marketing/_inbox/2026-05-20-hermes-truth-audit/{alex-internal-hermes,nousresearch-hermes-public,vault-history-timeline,jack-roberts-hermes-architecture}.md`
- Autonomy patterns research: `~/Projects/research-vault/research/2026-05-20-hermes-autonomy-patterns-mid-2026.md`
- Decision (next): `_meta/decisions/2026-05-21-capability-build-sequence.md` — Phase 3 of the plan, selects 3-5 items from the queue + locks the pin decision
- Community index: `github.com/0xNyk/awesome-hermes-agent`
- Top community projects: `github.com/witt3rd/oh-my-hermes`, `github.com/stainlu/hermes-labyrinth`, `github.com/Rainhoole/hermes-agent-acp-skill`, `github.com/Lethe044/hermes-incident-commander`
