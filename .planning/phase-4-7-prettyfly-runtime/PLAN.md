---
phase: 4.7
title: PrettyFly Runtime — bare-metal cutover
status: chartered (per ADR-006); awaiting pre-greenlight gates before kickoff
mode: TECH
depth: deep
date: 2026-05-06
adr: ~/Projects/agents/_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md
research: ~/Projects/research-vault/research/2026-05-06-jack-roberts-thesis-bare-metal-hermes-replacement.md
prior_decisions:
  - ~/Projects/agents/_meta/decisions/2026-05-04-adopt-hermes.md (now amended)
  - ~/Projects/agents/_meta/decisions/2026-05-04-vanclief-world-model-audit.md
  - ~/Projects/agents/_meta/decisions/2026-05-05-substrate-architecture.md
  - ~/Projects/agents/_meta/decisions/2026-05-05-slack-ecosystem-pivot.md
  - ~/Projects/agents/_meta/decisions/2026-05-05-litellm-routing-stack.md
operator: alex
---

# Phase 4.7 — PrettyFly Runtime detailed plan

## §0 Mission

Replace the third-party Hermes Agent runtime (Nous Research, MIT, v0.12.0 — currently 261 commits behind upstream) with **PrettyFly Runtime (PF Runtime)**, a custom Python agent runtime owned end-to-end at `~/Projects/agents/pf-runtime/`. Ship as MIT-licensed source eligible for Scale-tier on-prem deliverables. Cutover via 14-day parallel shadow against Hermes; data-driven five-gate evaluation with no hybrid mode after cutover. Schedule between Phase 4.5 (LAIK-as-MCP fusion) and Phase 5 (gravity-claw retirement). Per ADR-006 §6, all six locked operator commitments hold.

## §1 Pre-greenlight gates (BEFORE Phase 4.7 kickoff)

These three gates fire _before_ a single line of PF Runtime code ships. Each can defer Phase 4.7 indefinitely without violating ADR-006 — ADR-006 commits to the bare-metal _direction_, not the timeline.

### Gate G0 — Marketplace GTM dependency confirmation

**Question:** Does Phase 5 (PrettyFly OS marketplace launch) actually depend on owning the runtime, or does it ship cleanly on Hermes v0.12.0?

**Why this gate exists:** Specialist board's economist lens estimated total cost at ~$76K (build + shadow + 3-yr maintenance) and value at $46.5K–$426K — median $150K — but explicitly _only if marketplace GTM depends on the runtime differentiation_. If Phase 5 launches Lite/Pro tiers on Hermes today and Scale-tier on-prem ships at a later date with whichever runtime is mature, Phase 4.7 becomes a ~6-week tax with no near-term revenue lift. If Scale-tier explicitly markets "MIT-licensed runtime, 100% your source" as a regulated-SMB moat, Phase 4.7 unlocks revenue.

**How to clear:**

1. Read `~/Projects/research-vault/research/2026-05-04-company-agi-laik-hermes-fusion.md` §5 (three-tier pricing) and §4 (competitive landscape).
2. Confirm in writing with operator: "Scale-tier on-prem (\$9,999/mo) requires PF Runtime as a differentiator vs Glean/Hebbia/Sierra/Decagon/MS Copilot Tuning, and the marketing/sales motion will explicitly cite open runtime source as a moat."
3. If yes → proceed to G1. If no → defer Phase 4.7 to Q3 2026 post-marketplace-launch and revisit when 5+ tenants are onboarded; document the deferral as ADR-007.

**Owner:** alex (operator decision; non-delegable)

### Gate G1 — Hermes baseline measurement

**Question:** What does Hermes v0.12.0 actually score on our 30-question golden set under our real workload, and what is its actual cost-per-session profile?

**Why this gate exists:** The 4.7.5 cutover gate compares PF Runtime to "Hermes baseline" — but if Hermes itself fails Ragas ≥0.85 on the golden set, the gate criterion is unrealistic and PF Runtime might be unfairly judged. Specialist board's cross-cutting finding #1 makes this load-bearing: "Establish Hermes' own Ragas baseline on the golden set _before_ committing to the 4.7.2 gate."

**Workspace isolation (clarified per review).** G1 runs in a **dedicated shadow workspace** — _not_ the live Phase 1 personal-profile workspace. Concretely: a copy of `personal/` profile dir at `~/.hermes/profiles/personal-baseline/` with its own LiteLLM API-key alias (`personal-baseline-tier-cheap`), its own Langfuse project (`hermes-baseline-2026-05`), and its own Slack/Telegram credentials pointing at a private bot used only for measurement. Phase 1's live shadow-vs-gravity-claw comparison is unaffected and continues to run on the canonical `personal/` profile. The two workspaces share the same SOUL/USER/MEMORY/CLAUDE files (read-only at runtime in both) so the measurement is apples-to-apples; only credentials and API-key aliases are forked. **Sequencing:** G1 fires _after_ Phase 1's first 24h of live traffic (so the personal profile's Hermes session DB has real conversation history to stabilize MEMORY.md against), but the 7-night G1 capture itself runs entirely in `personal-baseline/`.

**How to clear:**

1. Provision the shadow workspace: `scripts/clone-profile-baseline.sh personal personal-baseline` — copies profile dir, mints LiteLLM key alias, creates Langfuse project.
2. Run `scripts/email-triage-eval-nightly.sh --profile personal-baseline` and the personal-profile golden set under Hermes v0.12.0 for 7 consecutive nights.
3. Capture: Promptfoo Wilson lower-CI per profile, Ragas faithfulness per profile, cost-per-session p50/p95, p95 latency, trace volume per 24h.
4. Write `~/Projects/agents/.planning/phase-4-7-prettyfly-runtime/baseline/HERMES_BASELINE.md` with the captured numbers + sample size.
5. If Hermes scores ≥0.85 Ragas → 4.7.2 gate is "match Hermes ±0.02." If Hermes scores 0.80–0.85 → gate is "match Hermes ±0.02 AND clear 0.80 floor." If Hermes scores <0.80 → halt: the issue is upstream of runtime choice.

**Owner:** PF Runtime build lead. Calendar: 7 days. Fires concurrent with Phase 1 (no operational conflict because Phase 1 runs on canonical `personal/`, G1 runs on isolated `personal-baseline/`).

### Gate G2 — Hermes feature audit (current actual usage across 13 profiles)

**Question:** Which Hermes features do our 13 profiles actually use today vs which are dormant in the v0.12.0 install?

**Why this gate exists:** Skeptic finding #2 + architecture finding #4: dream-loop and skill self-generation are the least-documented parts of Hermes; we may be planning to replicate features no profile uses, OR we may be missing features that quietly run in the background and would silently disappear at cutover.

**How to clear:**

1. `grep -r "skill_manager_tool\|kanban_tools\|memory_tool" ~/.hermes/profiles/*/` → count usage per profile.
2. Read `~/.hermes/sessions/` SQLite DBs → count `CREATE skill` events, dream-loop firings, Kanban task spawns per profile over 30 days.
3. Read Langfuse traces filtered by `tool_name` → identify the 80th-percentile-used tool per profile.
4. Write `~/Projects/agents/.planning/phase-4-7-prettyfly-runtime/HERMES_FEATURE_USAGE.md`. For each Hermes feature: in-use (yes/no), profiles using it, frequency, criticality.
5. PF Runtime sub-phase 4.7.2 ships only the features where in-use=yes for ≥1 profile. Dormant features get noted as deferred-by-design.

**Owner:** PF Runtime build lead. Calendar: 2 days. Fires after G1 baseline is captured.

**All three gates must clear before any code in `pf-runtime/` is written.** Pre-work artifacts in §10 (LAIK MCP boundary lock, profile-dir contract test, Hermes commit-watcher) can fire in parallel with these gates because they reduce risk for both Phase 4.5 and Phase 4.7 regardless of go/no-go outcome.

## §2 Reversibility ledger

| Sub-phase                    | Class  | Cost if wrong                                                                                                     | Recommendation                                                                               |
| ---------------------------- | ------ | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| G0 marketplace dependency    | TYPE-2 | Low — defer Phase 4.7 to Q3, no sunk cost                                                                         | If unclear, ask operator and wait                                                            |
| G1 Hermes baseline           | TYPE-2 | Low — measurement only                                                                                            | Run it; cheap insurance                                                                      |
| G2 feature audit             | TYPE-2 | Low — read-only inspection                                                                                        | Run it; cheap insurance                                                                      |
| 4.7.0 pre-work artifacts     | TYPE-2 | Low — design docs and contract tests                                                                              | Ship before code                                                                             |
| 4.7.1 Loop primitive         | TYPE-1 | High — commits to PF Runtime event-loop semantics; reverting requires re-credentialing 13 profiles back to Hermes | Pre-shadow preflight on 1 profile for 48 hours before committing to full build               |
| 4.7.2 Memory + skills        | TYPE-1 | High — schema commit; Ragas failure means episodic memory recovery from Langfuse traces                           | Hermes baseline (G1) sets the floor; mock LAIK MCP locally if Phase 4.5 ships late           |
| 4.7.3 Channel gateway        | TYPE-2 | Medium — channel adapter crash recovers from Honcho buffer + Langfuse trace replay                                | Slack first (already planned per ADR-004); Telegram/Email/Discord follow once Slack is green |
| 4.7.4 Kanban + Fleet Console | TYPE-2 | Medium — Postgres schema is additive; rollback is `DROP TABLE pf_kanban_*`                                        | Use existing mission-control Postgres; don't reinvent                                        |
| 4.7.5 Cutover                | TYPE-1 | Massive — binary, no hybrid; failure = stay on Hermes and document gaps in follow-up ADR                          | All five gates must clear in same 14-day shadow run                                          |

**Cross-reversibility:** Sub-phases 4.7.1, 4.7.2, and 4.7.5 are TYPE-1. Mitigation pattern: each TYPE-1 step is gated by a measurement (golden-set token delta, Ragas score, five-gate cutover) and a rollback that reverts to Hermes v0.12.0. The frozen Hermes pin is the safety net.

## §3 ROI snapshot

| Item                                 | Estimate                                                         | Notes                                                                                                                                                                                                    |
| ------------------------------------ | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Build cost                           | 400–500 hours @ $150/hr loaded ≈ **$60–75K**                     | 1 FTE × 5–6 weeks. Includes Hermes feature-parity rework (dream loop, skill self-gen, Kanban edge cases) and 14-day shadow operational supervision.                                                      |
| 14-day shadow operating cost         | **$0.8–1.2K**                                                    | 2× Langfuse trace volume; 2× LiteLLM proxy passthrough (proxy adds no token cost; LLM cost doubles). 13 profiles × ~30K msg × 2 runtimes ≈ 780K events. Mitigated by `tier-cheap` default during shadow. |
| 3-yr operational TCO delta vs Hermes | **+$22.5K saved (net)**                                          | Hermes-churn maintenance saved (~250 hrs over 3 years porting upstream churn at $150/hr) minus PF Runtime self-maintenance (~$15K).                                                                      |
| Marketplace strategic value          | **+$100K–500K** (median $150K)                                   | Scale-tier on-prem differentiation: $3–5K/mo uplift × 50 tenants over 2 years × 20% capture rate. **Conditional on G0 clearance.**                                                                       |
| BATNA — stay on Hermes               | **~$10K expected risk cost**                                     | 25% probability of forced fork or migration on Hermes v0.13+ over 18 months × $40–60K cost = $10K expected.                                                                                              |
| **Net 3-yr position vs BATNA**       | **+$46.5K to +$426K (median +$150K) IF G0=YES; ~–$66K IF G0=NO** | The marketplace GTM dependency dominates the math.                                                                                                                                                       |

## §4 Karpathy-ladder pacing

Each sub-phase ships **one thing end-to-end against a measured number**. The gate is a measurement, not a checklist. Phases never collapse — faster gate clearance is velocity, not a license to skip. Throwaway-version-first applies inside each sub-phase: ship the minimum that passes the gate, then iterate within the sub-phase if the next sub-phase's prerequisites surface.

## §5 Risk register

Consolidated from skeptic, architecture, reversibility, and concurrency lenses.

| ID  | Risk                                                                                                                                                                         | Severity | Likelihood | Mitigation                                                                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Money-pipeline silent break during shadow (ConsultOps Marc / sportsbook / lawdbot / YEH-ops drops a profile-routing event but Promptfoo + Ragas both pass on synthetic data) | **High** | Medium     | Per-profile real-job execution gate added to 4.7.5 (see §11). Sentry P0 alerts wired before shadow start. Skeptic-finding-1.                                                                                            |
| R2  | LAIK MCP boundary deferred to Phase 4.5 ships an interface that Hermes consumes implicitly but PF Runtime cannot consume cleanly                                             | **High** | Medium     | LAIK MCP spec lockdown is now PRE-WORK ITEM A (fires immediately, not deferred). Architecture-critical-finding-2.                                                                                                       |
| R3  | SQLite-for-Kanban write contention under 13-profile concurrent load → wall-clock spikes, dropped WebSocket dashboard updates                                                 | **High** | High       | **Switch Kanban store to Postgres** (reuse mission-control's existing Neon/Supabase Postgres). Architecture-finding-3 + concurrency-finding-A.                                                                          |
| R4  | Dream loop + skill self-gen runaway (skill spawns skill spawns skill) under 24h soak                                                                                         | Medium   | Medium     | `pf-runtime/docs/SKILL_SELF_GEN_BOUNDS.md` defines hard caps (3 skills/72h/profile, 100 LOC max per skill, cost ceiling per profile tier). 4.7.2 gate includes 24h sandbox + bound-check audit. Architecture-finding-4. |
| R5  | 4-tier memory consistency under concurrent skill-gen + dream-loop write paths                                                                                                | Medium   | Medium     | `pf-runtime/docs/MEMORY_LIFECYCLE.md` defines read-through ordering, write barriers, dream-loop merge semantics. Test: 100-message corpus concurrent run with consistency check. Architecture-finding-1.                |
| R6  | Cost ±10% gate is backward-looking; PF Runtime may have different scaling profile (single-threaded vs Hermes' parallelism)                                                   | Medium   | High       | Replace cost ±10% with **p95 latency ≤150% of Hermes baseline** + **concurrent throughput ≥80% of baseline**. Run 2-hour load test against synthetic workload before day 14. Skeptic-finding-4.                         |
| R7  | Slack Socket Mode message duplication during shadow if same workspace serves both runtimes                                                                                   | Medium   | Medium     | Use **dedicated shadow workspace** with 13 mirror channels (`#shadow-atlas-ceo`, etc.) + idempotency keys at Kanban store layer (Slack `event_id` hash). Concurrency-finding-B.                                         |
| R8  | ADR-006 lock creates rationalization risk: gates softened to confirm pre-decided cutover                                                                                     | Medium   | Low        | Explicit no-go criteria in §13. Operator names a "hold to Hermes" decision criterion before shadow start. Skeptic-finding-5.                                                                                            |
| R9  | Pilot profile selection bias collapses 14-day shadow: low-volume profile passes too easily, high-volume profile blows up at end                                              | Medium   | Medium     | **Pilot ladder**: 48h micro-pilot (`personal`, lowest volume) → 72h mid-pilot (`atlas-ceo`, planned-not-yet-active) → 14d full-fleet shadow. Skeptic-finding-3.                                                         |
| R10 | Hermes ships a security-relevant fix during the 4-6 week build window                                                                                                        | Low      | Medium     | Pre-work item D (Hermes commit-watcher daily diff to `forge-audit`). Port manually if security-critical; do NOT run `hermes update`. ADR-006 stop-condition.                                                            |
| R11 | LOC overrun: feature-parity scope drifts beyond 4,500 LOC                                                                                                                    | Medium   | Medium     | Per-sub-phase LOC budget locked below; if any sub-phase exceeds 130% of estimate, halt and re-evaluate. Drop priorities: Kanban first, channel adapters never.                                                          |
| R12 | Fly-by-night dependency (Hermes upstream) ships an MIT → AGPL re-license between today and cutover                                                                           | Low      | Low        | Pin install at v0.12.0 (already MIT). Periodic license-text snapshot in `forge-audit` profile.                                                                                                                          |

## §6 Sub-phase 4.7.0 — Pre-work artifacts (gates the build)

These four design documents and tests must ship before sub-phase 4.7.1 begins. They are not optional — they exist precisely because the perspective findings showed silent coupling risks. Calendar: 3-5 days, can run in parallel with G1 + G2 above.

### 4.7.0.A — `pf-runtime/SPEC.md` (runtime surface contract)

**Deliverable:** ~600 LOC markdown defining:

- Profile loader contract: `load_profile(slug: str) -> Profile` → `Profile` dataclass with `soul: str, user: str, memory: str, claude: str, manifest: Manifest, config: Config, a2a_card: A2ACard, pricing: Pricing` fields. Fields are read-only after load.
- Channel adapter ABC: `Channel` ABC with `async def receive(self) -> AsyncIterator[InboundMessage]`, `async def send(self, msg: OutboundMessage) -> None`, `async def typing(self, on: bool) -> None`, `async def ack(self, message_id: str) -> None`. Concrete adapters MUST be drop-in replaceable.
- Tool dispatch protocol: `Tool` ABC with `name: str, description: str, parameters: JSONSchema, async def invoke(self, args: dict, context: ToolContext) -> ToolResult`. `ToolContext` carries `profile_slug, session_id, langfuse_trace_id, mutation_proposal_callback`.
- Memory tier interfaces: see 4.7.0.B.
- Kanban store schema: see 4.7.0.C.

**Test:** `tests/spec_self_consistency.py` — assert every named contract has a stub implementation in `pf-runtime/stubs/`. Failing this test means SPEC.md cites APIs that nobody can build against.

**LOC estimate:** 600 markdown + 200 stubs.

### 4.7.0.B — `pf-runtime/docs/MEMORY_LIFECYCLE.md` (4-tier consistency rules)

Architecture-finding-1 fix. Defines:

- **Read-through cache ordering:** SOUL.md → SQLite buffer → LAIK MCP episodic → agentskills.io skills, fall-through on cache miss.
- **Write barriers:** Tier 1 (SOUL.md) is read-only at runtime — only edited via human commits. Tier 2 (SQLite buffer) writes synchronously, blocking. Tier 3 (LAIK episodic via MCP) writes async with a 30-second batch flush. Tier 4 (skills) writes synchronously after skill-gen approval.
- **Dream-loop merge semantics:** dream loop runs post-session, async, idempotent. Reads tier 2 (last 24h buffer) + tier 3 (last 24h episodic) → produces a candidate MEMORY.md diff → applies via `git apply` (operator-approved) or autonomously on personal profile only (others require operator approval per §11).
- **Concurrency invariant:** during dream-loop compaction, tier 2 buffer is read-only. New writes to tier 2 are queued and applied after compaction completes (typically <30s).

**Test:** `tests/memory_consistency_test.py` — concurrent skill-gen + dream-loop on a 100-message corpus; assert (a) zero lost writes, (b) read-after-write within tier 2 returns the latest write, (c) post-compaction tier 2 + tier 3 view is consistent.

**LOC estimate:** 400 markdown + 250 test.

### 4.7.0.C — `pf-runtime/docs/SKILL_SELF_GEN_BOUNDS.md` (runaway safeguards)

Architecture-finding-4 fix. Defines:

- **Per-profile cap:** ≤3 new skills per 72h.
- **Per-skill LOC ceiling:** ≤100 LOC per skill markdown (excluding code blocks; code blocks ≤300 LOC).
- **Cost ceiling:** skill-gen invocations cap at 10% of profile's daily LiteLLM tier budget (per ADR-005 tier mapping).
- **Episodic store limit:** ≤50 skill mutations per profile per day.
- **Bound-check audit:** dream loop checks all four bounds at end of each session; if any breached → halt skill-gen for that profile + alert via `forge-audit`.

**Test:** `tests/skill_gen_bounds_test.py` — synthetic 24h run with rate-limit-bypass attempt; assert all four bounds enforced + alert fires on breach.

**LOC estimate:** 200 markdown + 200 test.

### 4.7.0.D — `pf-runtime/docs/ADAPTER_PLUGIN_INTERFACE.md` (channel adapter ABC formalization)

Architecture-finding-5 fix. Repeats the `Channel` ABC from SPEC.md but with implementation-level detail:

- Method-by-method contract (return types, error contracts, idempotency requirements).
- Lifecycle: `connect → run (yields incoming) → send (handles outbound) → disconnect`.
- Failure-mode contract: connection drops emit `ChannelError`; runtime retries with exponential backoff up to `max_reconnect_attempts: 5` then surfaces to operator.
- Idempotency contract: outbound messages MUST carry `message_id` (UUIDv7 by default); duplicate sends are no-ops.

**Test:** `tests/channel_abc_test.py` — mock `Channel` implementation; runtime exercises the full lifecycle; chaos test injects connection drops; assert zero message duplication and no missed messages.

**LOC estimate:** 300 markdown + 350 test.

### 4.7.0.E — Profile-dir contract test (already in §10 pre-work)

`tests/profile_dir_contract.py` runs nightly; assert all 13 profile dirs in `~/Projects/agents/hermes/profiles/{name}/` are loadable by both the Hermes profile loader (today) and the PF Runtime profile loader (per SPEC.md). Failing means a profile drift would silently break the runtime swap.

**LOC estimate:** 150 LOC.

### 4.7.0 gate

All five artifacts exist, all five tests pass against stubs, peer review by Codex (`closeout-stack --mode=codex` per project convention) with ≤2 critical findings remaining.

## §7 Sub-phase 4.7.1 — Loop primitive

**Mission:** ship the agent loop as ~600 LOC of Python that runs the `personal` profile through one Slack DM round-trip via the LiteLLM proxy and produces the same tool calls Hermes would have produced for the same input.

### Files

| Path                                   | LOC est | Purpose                                                                                                                      |
| -------------------------------------- | ------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `pf-runtime/__init__.py`               | 30      | Package init, version                                                                                                        |
| `pf-runtime/__main__.py`               | 80      | CLI entry: `python -m pf-runtime run <profile>` + `pf-runtime kanban-worker --task-id <uuid>`                                |
| `pf-runtime/config.py`                 | 150     | Profile loader (reads `hermes/profiles/{slug}/` dir per SPEC.md)                                                             |
| `pf-runtime/runtime/loop.py`           | 350     | The while loop. Step counter, message history, finish-reason → break, interrupt handling, Langfuse trace correlation         |
| `pf-runtime/runtime/model_adapter.py`  | 120     | LiteLLM client at `http://127.0.0.1:4000`, async streaming, retry-on-429 with exponential backoff per ADR-005 tier semantics |
| `pf-runtime/runtime/tool_dispatch.py`  | 200     | MCP-aware tool execution, JSONSchema arg validation, error capture, streaming results back into message history              |
| `pf-runtime/runtime/stop_condition.py` | 80      | finish_reason parsing, step ceiling (default 8 per profile manifest), cost ceiling (per ADR-005), interrupt-flag check       |
| `pf-runtime/runtime/audit.py`          | 120     | Every step → Langfuse trace + SQLite mutation_audit (mirrors LAIK ADR-0001 pattern)                                          |

**Total:** ~1,130 LOC + ~250 LOC tests.

### Public API surface (function signatures)

```python
# pf-runtime/runtime/loop.py
async def run_session(
    profile: Profile,
    inbound: InboundMessage,
    *,
    channel: Channel,
    tools: list[Tool],
    memory: MemoryStack,
    audit: AuditSink,
    max_steps: int = 8,
    cost_ceiling_usd: float = 0.50,
) -> SessionResult:
    """Single-session agent loop. Returns when LLM emits finish_reason=='stop',
    step ceiling hit, cost ceiling hit, or interrupt requested."""

# pf-runtime/runtime/model_adapter.py
class LiteLLMAdapter:
    def __init__(self, base_url: str = "http://127.0.0.1:4000", tier: str = "tier-cheap", api_key_alias: str): ...
    async def stream_completion(self, messages: list[Message], tools: list[ToolSchema]) -> AsyncIterator[CompletionChunk]: ...
    async def cost_so_far(self, session_id: str) -> Decimal: ...

# pf-runtime/runtime/tool_dispatch.py
class ToolDispatcher:
    def __init__(self, tools: list[Tool], context: ToolContext): ...
    async def dispatch(self, name: str, args: dict) -> ToolResult: ...
    def validate_args(self, name: str, args: dict) -> None: ...  # raises ToolValidationError
```

### Test plan

- **Golden-set regression** (`tests/golden_set_regression.py`): 30 questions from `~/Projects/agents/hermes/profiles/personal/eval/golden.jsonl`. For each: run through PF Runtime loop, capture token count + tool-call sequence, compare to Hermes baseline from G1.
- **Interrupt test** (`tests/interrupt_test.py`): mid-session SIGINT delivery; assert clean shutdown with audit trail intact.
- **Cost-ceiling test** (`tests/cost_ceiling_test.py`): synthetic infinite-loop tool; assert cost ceiling triggers within 5% of configured limit.
- **Pre-shadow preflight** (cross-cutting finding #2): 48-hour run against `personal` profile in shadow mode, real Slack DM traffic mirrored from production. No write actions taken.

### Gate (4.7.1 → 4.7.2)

1. Token delta ≤ 5% vs Hermes baseline on 30/30 golden questions.
2. Tool-call sequence identical on 30/30 golden questions (set equality, not list equality — order can differ).
3. Pre-shadow preflight: 48 hours, zero unhandled exceptions, audit trail complete in Langfuse.
4. Codex review of `pf-runtime/runtime/` returns ≤1 critical finding.

### Risks specific to 4.7.1

- LiteLLM proxy gives different streaming chunk boundaries than Hermes' direct adapter → token count diverges artificially. **Mitigation:** measure token deltas at `usage` block in completion response, not chunk boundaries.
- The 30-question golden set was tuned for Hermes' tool registry; PF Runtime's tool registry must match. **Mitigation:** SPEC.md fixes tool naming convention.
- LiteLLM retry semantics differ from Hermes' retry semantics (LiteLLM retries on 429 by default; Hermes does its own backoff). **Mitigation:** disable LiteLLM retry, do retry in `model_adapter.py` with explicit semantics.

### Calendar

7–10 days for one engineer. Includes 48-hour preflight tail.

## §8 Sub-phase 4.7.2 — Memory + skills + dream loop

**Mission:** ship the 4-tier memory stack + skill self-gen + dream loop. Run 24 hours on the `personal` profile and clear Ragas + bounds-check gates.

### Files

| Path                                  | LOC est | Purpose                                                                                                                                                                                           |
| ------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------- | ---------- |
| `pf-runtime/memory/__init__.py`       | 30      | `MemoryStack` composer per MEMORY_LIFECYCLE.md                                                                                                                                                    |
| `pf-runtime/memory/tier1_soul.py`     | 60      | SOUL.md / USER.md / CLAUDE.md read-only loader; mtime watcher for hot reload                                                                                                                      |
| `pf-runtime/memory/tier2_buffer.py`   | 200     | SQLite WAL rolling buffer, per-profile DB at `pf-runtime/runtime-state/{slug}/buffer.sqlite`. Concurrent-safe per MEMORY_LIFECYCLE.md write barrier. Append-only with TTL eviction (last 30 days) |
| `pf-runtime/memory/tier3_episodic.py` | 150     | LAIK MCP client (consumes Phase 4.5 deliverable). Async batch flush every 30s. Falls back to local cache on MCP unavailability                                                                    |
| `pf-runtime/memory/tier4_skills.py`   | 100     | agentskills.io progressive-disclosure loader. Reads `~/Projects/agents/hermes/profiles/{slug}/skills/` + `~/.hermes/skills/` (shared)                                                             |
| `pf-runtime/skill_gen/self_author.py` | 150     | After 5+ tool-call session, prompt LLM to extract pattern → emit candidate skill.md. Subject to SKILL_SELF_GEN_BOUNDS.md hard caps                                                                |
| `pf-runtime/skill_gen/approver.py`    | 80      | Operator approval flow for skills outside the `personal` profile (per profile manifest `skill_gen_autonomy: auto                                                                                  | approve | disabled`) |
| `pf-runtime/dream/post_session.py`    | 180     | Post-session async hook. Reads tier 2 + tier 3 last-24h, prompts LLM to emit MEMORY.md diff + flag contradictions. Idempotent (uses session_id as compaction key)                                 |
| `pf-runtime/dream/bounds_audit.py`    | 100     | End-of-session bound check per SKILL_SELF_GEN_BOUNDS.md. Halts skill-gen for the profile + alerts forge-audit on breach                                                                           |

**Total:** ~1,050 LOC + ~400 LOC tests.

### Test plan

- **Ragas faithfulness regression** (`tests/ragas_faithfulness.py`): 30-question golden set + Ragas evaluator. Assert score within 0.02 of Hermes baseline (G1).
- **Skill auto-author test** (`tests/skill_self_gen_test.py`): synthetic 5+ tool-call session; assert skill.md emitted with correct frontmatter; assert SKILL_SELF_GEN_BOUNDS.md caps respected on rate-limit-bypass attempt.
- **Dream-loop diff test** (`tests/dream_loop_test.py`): synthetic conflicting messages in tier 2; assert dream loop produces non-empty MEMORY.md diff + flags the contradiction with line numbers.
- **Memory consistency test** (`tests/memory_consistency_test.py` from 4.7.0.B): 100-message corpus + concurrent skill-gen + dream-loop; assert tier 2 + tier 3 consistency under contention.
- **24-hour soak** (`scripts/4-7-2-soak.sh`): personal profile running on PF Runtime for 24 hours; capture (a) ≥1 skill auto-authored, (b) ≥1 dream-loop firing with non-empty diff, (c) zero bounds breaches, (d) Ragas score within target.

### Gate (4.7.2 → 4.7.3)

1. Ragas faithfulness ≥ 0.85 OR ≥ Hermes baseline – 0.02 (whichever is higher) on 30-question golden set.
2. ≥1 skill auto-authored during 24h soak; skill passes lint (`scripts/validate-skill.sh`).
3. ≥1 dream-loop firing during 24h soak; non-empty diff; contradiction flagging works on synthetic test data.
4. Zero SKILL_SELF_GEN_BOUNDS.md breaches during soak.
5. Memory consistency test passes.

### Risks specific to 4.7.2

- LAIK MCP from Phase 4.5 ships late or with incompatible interface → Tier 3 stuck. **Mitigation:** local SQLite fallback (mock MCP) lets 4.7.2 ship without blocking on Phase 4.5.
- Dream loop produces over-aggressive diffs that delete useful memory. **Mitigation:** diffs are operator-approved on profiles other than `personal`. Personal profile in shadow during 24h soak — operator reviews diffs at end-of-day.
- Ragas baseline lower than expected → 4.7.2 gate becomes "match Hermes ±0.02" which may be too generous. **Mitigation:** if Hermes baseline <0.80, halt — issue is upstream of runtime.

### Calendar

7–10 days for one engineer. Includes 24-hour soak.

## §9 Sub-phase 4.7.3 — Channel gateway

**Mission:** ship Slack adapter (per ADR-004) first, then Telegram + Email + Discord. Money-pipeline OAuth scopes remain read-only on `vanclief` and `sportsbook` (no `chat:write`/`im:write`/`reactions:write`/`files:write`).

### Files

| Path                                        | LOC est | Purpose                                                                                                                                                                                                                                   |
| ------------------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pf-runtime/channels/__init__.py`           | 30      | Channel registry                                                                                                                                                                                                                          |
| `pf-runtime/channels/adapter_base.py`       | 100     | `Channel` ABC per ADAPTER_PLUGIN_INTERFACE.md                                                                                                                                                                                             |
| `pf-runtime/channels/slack.py`              | 250     | slack-bolt + Socket Mode + per-app OAuth tokens from macOS Keychain (`security find-generic-password -s slack-bot-{slug}`). Idempotency keys via `event_id`. 13 concurrent app connections                                                |
| `pf-runtime/channels/telegram.py`           | 200     | python-telegram-bot 21.x; long-polling default; webhook mode optional                                                                                                                                                                     |
| `pf-runtime/channels/email.py`              | 150     | aioimaplib + aiosmtplib; per-profile mailbox; thread-tracking via `In-Reply-To` headers                                                                                                                                                   |
| `pf-runtime/channels/discord.py`            | 150     | discord.py 2.x; gateway connection per profile; voice deferred                                                                                                                                                                            |
| `pf-runtime/channels/keychain.py`           | 80      | macOS Keychain bridge: `security find-generic-password -w` wrapped in async-safe accessor; falls back to `.env` for non-Mac dev                                                                                                           |
| `pf-runtime/channels/voice/whisper_loop.py` | 150     | Slack `file_shared` audio events → Groq Whisper Turbo → text reply pipeline (parity with `~/Projects/agents/hermes/profiles/personal/skills/voice-loop/`). Deferred-by-design out of MVP — ships in 4.7.3.B follow-up if calendar permits |

**Total (without voice):** ~960 LOC + ~350 LOC tests. With voice: +150 LOC.

### Test plan

- **Channel ABC contract test** (from 4.7.0.D): chaos test on mock channel; zero duplication, zero missed.
- **Slack 50-message parity test** (`tests/slack_parity.py`): 50 inbound messages on `atlas-ceo` shadow workspace; PF Runtime + Hermes both process; assert identical action sequences (`set` equality on tool calls; `≤5%` token delta on summarized response text).
- **Money-pipeline OAuth scope test** (`tests/money_pipeline_oauth.py`): assert vanclief and sportsbook tokens lack `chat:write`/`im:write`/`reactions:write`/`files:write` (read directly from Slack `auth.test` API).
- **Idempotency test** (`tests/slack_idempotency.py`): inject duplicate inbound `event_id`; assert second invocation is no-op (verified at Kanban store layer per concurrency-finding-B).
- **Reconnect test** (`tests/slack_reconnect.py`): kill Socket Mode connection mid-session; assert reconnect within 5s with backoff; zero message loss.

### Gate (4.7.3 → 4.7.4)

1. 50-message parity test: 50/50 identical action sequences on `atlas-ceo`.
2. Money-pipeline OAuth scope test: 0 write scopes on vanclief + sportsbook.
3. Idempotency test: 100% duplicate suppression.
4. Reconnect test: 0 message loss across 10 connection drops.
5. Per-channel preflight: 24-hour smoke on Slack only (Telegram/Email/Discord ship after Slack is green).

### Risks specific to 4.7.3

- 13 concurrent Socket Mode connections exceed slack-bolt's tested envelope → connection drops cascade. **Mitigation:** per-channel reconnect with jitter; max 1 reconnect per second across the fleet.
- Per-profile Keychain access on Mac requires user consent dialog on first call → blocks daemon startup. **Mitigation:** pre-warm Keychain on operator login via `scripts/keychain-warm.sh`; daemon fails fast if Keychain unavailable.
- Email thread tracking via `In-Reply-To` is fragile in some clients → broken threading. **Mitigation:** secondary tracking via custom `X-PF-Thread-ID` header.

### Calendar

7–10 days for Slack + Telegram + Email + Discord (Slack first, others sequential). Voice deferred to 4.7.3.B.

## §10 Sub-phase 4.7.4 — Kanban + Fleet Console + 14-day shadow

**Mission:** ship the Kanban store on **Postgres** (not SQLite — per architecture-finding-3 + concurrency-finding-A) plus REST/WebSocket API plus Fleet Console extension at `~/Projects/mission-control/api-cost-dashboard/`. Run all 13 profiles on PF Runtime in shadow alongside Hermes for 14 days.

### Files

| Path                                                                                        | LOC est | Purpose                                                                                                                                    |
| ------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `pf-runtime/kanban/__init__.py`                                                             | 30      | Package                                                                                                                                    |
| `pf-runtime/kanban/schema.sql`                                                              | 100     | Postgres schema: `pf_kanban_tasks`, `pf_kanban_transitions`, `pf_kanban_audit`. Sibling schema in mission-control's existing Neon Postgres |
| `pf-runtime/kanban/store.py`                                                                | 180     | asyncpg-backed Kanban store. CRUD + state-machine transitions. Idempotency key on `(profile_slug, message_id)` per concurrency-finding-B   |
| `pf-runtime/kanban/api.py`                                                                  | 130     | FastAPI: REST `GET /tasks`, `POST /tasks`, WebSocket `/tasks/stream` for real-time                                                         |
| `pf-runtime/kanban/worker.py`                                                               | 100     | Async worker: claims tasks, runs `pf-runtime run-kanban-task --id <uuid>` per task                                                         |
| Fleet Console extension at `~/Projects/mission-control/api-cost-dashboard/src/pages/fleet/` | 200     | Next.js page: per-profile status, recent tasks, cost-per-session, p95 latency, trace volume. Reads PF Runtime Kanban API + Langfuse        |

**Total:** ~740 LOC + ~250 LOC tests.

### Migration to Postgres (was SQLite per ADR-006)

ADR-006 §3 cited "SQLite-backed task board" — this PLAN supersedes that with Postgres for Kanban only. Tier 2 memory buffer remains SQLite (per-profile, low-concurrency). Justification: architecture-finding-3 + concurrency-finding-A. Action: amend ADR-006 §3.7 with the Kanban-on-Postgres correction at the next ADR sweep.

### Test plan

- **SQL load test** (`tests/kanban_load_test.py`): 13 profiles × 100 concurrent task writes/reads; p95 write latency <100ms; p99 <500ms.
- **WebSocket subscriber test** (`tests/kanban_websocket_test.py`): 5 simultaneous dashboard subscribers; broadcast latency <250ms.
- **Pilot ladder** (per skeptic-finding-3):
  1. **48h micro-shadow** on `personal` (lowest volume): all 13 profiles' configs loaded, only `personal` actually receives traffic. Assert no profile contention.
  2. **72h mid-shadow** on `personal` + `atlas-ceo` (planned-not-yet-active): assert two-profile concurrency under realistic strategy-doc workload.
  3. **14-day full-fleet shadow**: all 13 profiles active on PF Runtime alongside Hermes.

### Gate (4.7.4 → 4.7.5)

The Kanban itself ships when SQL load test + WebSocket test pass. The 14-day shadow has its own five-gate evaluation in §11.

### Calendar

5–7 days build + 14 days shadow.

## §11 Sub-phase 4.7.5 — Cutover

**Mission:** evaluate the 14-day shadow against the five gates. If all five pass, cut over. If any fail, halt and document.

### The five gates (revised per skeptic-finding-1 and skeptic-finding-4)

1. **Promptfoo eval ≥ 85% Wilson-CI lower-bound per profile** on the existing `email-triage-eval-nightly` golden set. Per-profile failures are not averaged — every profile clears or no profile cuts over.
2. **Ragas faithfulness ≥ Hermes baseline – 0.02** on personal profile golden set (calibrated against G1 baseline).
3. **Per-profile real-job execution gate** (NEW per skeptic-finding-1): every profile completes ≥1 full real-world job through PF Runtime during shadow. ConsultOps Marc lead intake fires at least once; sportsbook predictions fire at least once; lawdbot Telegram message fires at least once; YEH-ops daily check-in fires at least once. Sentry + Langfuse trace each one end-to-end with zero P0.
4. **Latency gate** (NEW per skeptic-finding-4): p95 latency ≤150% of Hermes baseline; concurrent throughput ≥80% of baseline. Replaces the cost ±10% gate which was backward-looking.
5. **Zero P0 incidents** across the full 14-day shadow (Sentry-defined P0 = production data loss, security breach, or ≥1 hour outage of a money-pipeline profile).

### Cutover sequence

```
1. Final five-gate evaluation script: `scripts/4-7-5-cutover-gate.sh`
   → Reads Promptfoo TSV, Ragas score from G1+shadow run, Sentry P0 count,
     Langfuse latency p95, real-job execution audit log.
   → Returns CUT_OVER | HOLD with per-gate verdict.

2. If CUT_OVER:
   a. `hermes profile pause --all` (use Hermes' own kill switch for graceful drain)
   b. Wait 5 minutes for in-flight sessions to complete
   c. `systemctl stop hermes-runtime.service` (if running as service) or kill -TERM
   d. `mv ~/.hermes/profiles ~/.hermes/profiles.archived-{YYYY-MM-DD}/`
   e. `pf-runtime symlink-state --to ~/Projects/agents/pf-runtime/runtime-state/profiles/`
   f. `systemctl start pf-runtime.service`
   g. Smoke test: `pf-runtime healthcheck --all-profiles`
   h. Update `~/Projects/agents/docs/migration-runbook.md` phase pointer to "Phase 4.7 complete"
   i. Update MANIFEST.md status
   j. Tag git commit: `phase-4-7-cutover-{YYYY-MM-DD}`
   k. Begin 90-day forensic window: `~/.hermes/hermes-agent/` archive at `~/Projects/_archive/2026/hermes-v0-12-0-archive.tgz`

3. If HOLD:
   a. Document failed gate(s) in follow-up ADR (`ADR-007 — Phase 4.7 hold`).
   b. PF Runtime stays in shadow mode (not cut over); Hermes continues as primary.
   c. Re-evaluate after 30 days OR when failed-gate root cause is fixed (whichever comes first).
   d. Phase 5 (gravity-claw retirement) and Phase 6 (marketplace launch) proceed on Hermes if needed.
```

### Risks specific to 4.7.5

- Cutover happens during a money-pipeline event (ConsultOps Marc Excel sync at 4:30 PM CT). **Mitigation:** cutover only fires during a defined low-traffic window (Saturday 02:00 ET).
- Profile dirs symlink from Hermes mirror to PF Runtime canonical introduces stale state. **Mitigation:** dry-run the symlink swap on a copy of `~/.hermes/profiles/` before the real cutover.
- Operator changes mind post-cutover. **Mitigation:** archive at step (k) is a tarball; restore is `tar xzf + hermes profile resume --all`.

### Calendar

1 day cutover + 90-day archive maintenance.

## §12 3am test (observability)

If the on-call gets paged at 3am because PF Runtime threw a P0:

| Scenario                                                                                        | What fires                                                       | What on-call sees                                                                                | What's missing → ADD                                                                                                                                                        |
| ----------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ConsultOps profile drops a Marc lead intake event                                               | Sentry P0 (event signature: `pf-runtime.kanban.task_dropped`)    | Slack alert in `#consultops-ops` with task ID, profile, timestamp, last successful trace         | **ADD:** OTel attr `pf_runtime.profile_slug`, `pf_runtime.session_id`, `pf_runtime.kanban_task_id`. Sentry context: Langfuse trace URL, Postgres Kanban audit row reference |
| Slack Socket Mode connection storm (>5 reconnects in 60s on any profile)                        | Datadog metric `pf_runtime.channel.reconnects` exceeds threshold | PagerDuty page → on-call Slack DM with profile, error class, last-known-good timestamp           | **ADD:** Datadog metric label `profile_slug`. Status page banner if >3 profiles affected                                                                                    |
| Postgres Kanban write latency p95 >500ms for 5 minutes                                          | Postgres alerting + Langfuse trace tail                          | Slack alert in `#agents-ops`, Grafana dashboard URL with last 1h latency histogram               | **ADD:** Grafana dashboard at `grafana.internal/d/pf-runtime-kanban`. Auto-attach last 50 slow-query log lines                                                              |
| LiteLLM proxy returns 5xx for >10% of calls in 5 minutes                                        | LiteLLM internal alert + Langfuse trace tail                     | Slack alert in `#agents-ops` with affected profile tier(s)                                       | **ADD:** OTel span tags `litellm.tier`, `litellm.fallback_used`. LiteLLM dashboard URL in alert                                                                             |
| Dream loop firing produces a MEMORY.md diff that deletes >50% of existing content (pruning bug) | `pf-runtime.dream.large_diff` Sentry event                       | Slack alert in `#vanclief` (per VanClief audit duty in ADR-002) with diff URL + affected profile | **ADD:** dream loop emits diff size metric + safety threshold trigger. Operator-approval-required mode for any profile with `skill_gen_autonomy: approve`                   |

## §13 No-go criteria (explicit per skeptic-finding-5)

These are the conditions under which Phase 4.7 holds at Hermes-pinned indefinitely. Operator names them ahead of time so a mid-stream failure isn't rationalized into a cutover.

| If                                                                | Then                                                              |
| ----------------------------------------------------------------- | ----------------------------------------------------------------- |
| G0 = NO (marketplace doesn't depend on runtime differentiation)   | Defer Phase 4.7 to Q3 2026 post-marketplace launch                |
| G1 Hermes baseline Ragas < 0.80                                   | Halt — issue is upstream of runtime choice, fix Hermes-side first |
| Pre-shadow preflight 4.7.1 reveals ≥3 unhandled exception classes | Halt sub-phase, fix root cause, restart preflight                 |
| 4.7.2 24h soak fails Ragas gate by ≥0.05 below baseline           | Halt — memory tier design is wrong, return to MEMORY_LIFECYCLE.md |
| 4.7.3 50-message Slack parity < 45/50 identical action sequences  | Halt — channel adapter has prompt-routing bugs                    |
| Any sub-phase exceeds 130% of LOC budget                          | Halt and re-evaluate scope                                        |
| Hermes ships a security-relevant fix mid-build                    | Pause sub-phase, port the fix manually to v0.12.0 pin, resume     |
| Operator names "stop" at any point                                | Stop. Document state. Continue on Hermes                          |

## §14 Pre-work that fires NOW (parallel with Phase 1)

These items reduce Phase 4.7 risk and improve Phase 4.5 quality regardless of go/no-go on Phase 4.7. They fire immediately.

| Item                                    | Owner                      | Calendar   | Deliverable                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------- | -------------------------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| **A. LAIK MCP boundary lock**           | Phase 4.5 lead             | 2 days     | `~/Projects/agents/mcp-servers/laik/SPEC.md` formalizing the 6-tool surface (laik_status, laik_list_tenants, laik_query, laik_sql, laik_propose_mutation, laik_confirm_mutation) with input/output JSONSchemas. `tests/laik_mcp_contract.py` validates Hermes's existing consumption pattern + a stub PF Runtime consumer. Architecture-critical-finding-2 |
| **B. Profile-dir contract test**        | PF Runtime build lead      | 3 hours    | `~/Projects/agents/tests/profile_dir_contract.py`. Nightly cron via launchd. Asserts all 13 profile dirs are loadable by Hermes today AND by the SPEC.md profile loader contract                                                                                                                                                                           |
| **C. Hermes commit-watcher**            | forge-audit profile config | 30 minutes | launchd job at `~/Library/LaunchAgents/com.prettyfly.hermes-commit-watcher.plist`. Runs daily 02:30 ET. `git -C ~/.hermes/hermes-agent fetch && git log --oneline HEAD..origin/main                                                                                                                                                                        | head -50 \| mail forge-audit@local`. Operator scans for security-relevant fixes; non-security commits ignored |
| **D. Hermes baseline measurement (G1)** | PF Runtime build lead      | 7 days     | `~/Projects/agents/.planning/phase-4-7-prettyfly-runtime/HERMES_BASELINE.md`. Promptfoo Wilson-CI per profile, Ragas per profile, p50/p95 cost-per-session, p95 latency, trace volume                                                                                                                                                                      |
| **E. Hermes feature audit (G2)**        | PF Runtime build lead      | 2 days     | `HERMES_FEATURE_USAGE.md`. Per-feature usage matrix across 13 profiles                                                                                                                                                                                                                                                                                     |
| **F. Pre-work design docs**             | PF Runtime build lead      | 3-5 days   | SPEC.md + MEMORY_LIFECYCLE.md + SKILL_SELF_GEN_BOUNDS.md + ADAPTER_PLUGIN_INTERFACE.md per §6                                                                                                                                                                                                                                                              |

Items A and C–E can run in parallel. Items B and F can run after A locks the LAIK MCP surface.

## §15 Verification

After cutover (post-4.7.5), verify success against these criteria:

- [ ] All 13 profiles running on PF Runtime; `hermes` binary not in any profile's runtime path
- [ ] Phase 5 (gravity-claw retirement) proceeds on PF Runtime without regression
- [ ] Phase 6 (marketplace launch) ships Scale-tier on-prem with PF Runtime as the runtime artifact (`pf-runtime-1.0.0.tar.gz`, MIT-licensed, ~3,500 LOC + tests)
- [ ] `forge-audit` profile reports zero unported security-relevant Hermes commits in the prior 30 days (or all relevant ones ported)
- [ ] Cost-per-session post-cutover ≤ 105% of Hermes baseline (after 30-day stabilization)
- [ ] VanClief weekly Sunday Brief explicitly cites "PF Runtime week N" with no critical findings
- [ ] One regulated-SMB tenant onboards to Scale-tier with on-prem PF Runtime within 90 days of cutover (success metric for the marketplace differentiation thesis from G0)

## §16 Total estimates and decision pointers

| Item                                | Estimate                                                                                                                                                                           |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Total LOC**                       | ~3,500-4,200 production + ~1,250 tests = **~4,750-5,450 total** (revised up from ADR-006's 2,500-3,500 estimate after architecture/concurrency findings)                           |
| **Total calendar**                  | 4-6 weeks build + 14-day shadow + 1 day cutover = **6-9 weeks elapsed**. Pre-work (G0/G1/G2 + items A-F) adds **2 weeks elapsed before kickoff** but runs in parallel with Phase 1 |
| **Total cost (per economist lens)** | $60-75K build + $0.8-1.2K shadow + $15K 3-yr maintenance = **~$76-91K**                                                                                                            |
| **Net 3-yr position vs BATNA**      | **+$46.5K to +$426K (median +$150K) IF G0=YES; ~–$66K IF G0=NO**                                                                                                                   |

## §17 First command to fire

When Alex confirms G0 (marketplace GTM dependency = YES):

```bash
# Day 1 of pre-work — fires the three gates that gate the build
cd ~/Projects/agents
mkdir -p .planning/phase-4-7-prettyfly-runtime/{baseline,feature-usage,specs}

# G1 — Hermes baseline measurement (7 days, parallel with Phase 1)
nohup ./scripts/email-triage-eval-nightly.sh --capture-baseline > .planning/phase-4-7-prettyfly-runtime/baseline/eval-night-1.log 2>&1 &

# G2 — Feature audit (2 days)
./scripts/hermes-feature-audit.sh --output .planning/phase-4-7-prettyfly-runtime/feature-usage/HERMES_FEATURE_USAGE.md

# Pre-work A — LAIK MCP boundary lock (Phase 4.5 lead picks this up)
echo "TODO: Phase 4.5 lead writes mcp-servers/laik/SPEC.md per Phase 4.7 PLAN.md §14.A"

# Pre-work C — Hermes commit-watcher
launchctl load ~/Library/LaunchAgents/com.prettyfly.hermes-commit-watcher.plist
```

The first commit on `pf-runtime/` happens _after_ G0=YES + G1 captured + G2 captured + four design docs reviewed. Estimated calendar to that first commit: **2 weeks of pre-work**, all of which is non-disruptive to Phase 1.

---

**End of plan.** ~5,400 words. Folds in five skeptic findings, five architecture findings, three reversibility/economist/concurrency-lens findings + three cross-cutting amplifications, and inventory data from `~/Projects/agents/` + `~/.hermes/hermes-agent/`. Awaiting operator confirmation on Gate G0 (marketplace GTM dependency) before kickoff.
