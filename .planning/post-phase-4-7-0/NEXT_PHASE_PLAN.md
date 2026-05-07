---
phase: post-4.7.0
title: Next-phase plan — the 7-day window between Phase 4.7.0 cleared and G1 baseline landing
status: draft, awaiting operator confirmation
mode: TECH
depth: deep
date: 2026-05-06
operator: alex
prior_phase_commit: a866abb (agents/main)
adr: ~/Projects/agents/_meta/decisions/2026-05-06-prettyfly-runtime-bare-metal.md
pf_runtime_plan: ~/Projects/agents/.planning/phase-4-7-prettyfly-runtime/PLAN.md
g1_target_landing: 2026-05-13
agency_agents_repo: msitarzewski/agency-agents (MIT, 225 .md persona specs at /tmp/agency-agents/)
---

# Next-phase plan — the 7-day window between 4.7.0 cleared and G1 landing

## §0 Mission

Decide what work fires in `~/Projects/agents/` between now (2026-05-06, Phase 4.7.0 PrettyFly Runtime pre-work cleared via commit `a866abb`) and the G1 Hermes baseline measurement landing (~2026-05-13). Operator asked to factor msitarzewski/agency-agents (MIT, 225 .md persona specs) as a first-class candidate. After full pipeline review (5 perspectives + 7-lens specialist board + pre-flight probes), the synthesized recommendation is **MEASURE-FIRST, DEFER MOST**: the dominant work in this window is repairing G1 readiness (which pre-flight reveals is incomplete) and capturing the baseline cleanly, not building new things or importing third-party agents on speculation.

## §1 Pre-flight reality check (read this first — UPDATED 2026-05-06 PM after vanclief audit)

VanClief's challenge ("is Phase 1 actually running") drove a deeper probe. Findings overturn the original frame of this document.

### §1.0 Phase 1 personal-profile shadow has NOT been running on Hermes

`hermes profile list` 2026-05-06 12:40 shows: **only `atlas-ceo` has a running gateway** (PID 1585). All 12 other profiles — including `personal` — show `Gateway = stopped`. `~/.hermes/active_profile = atlas-ceo`. Last hermes agent.log activity 2026-05-05 16:46 (registry plugin loads only, no session activity). Last write to `~/.hermes/profiles/personal/` was 2026-05-05 16:38 — config edits, not runtime traffic.

**Implication:** the Phase 1 acceptance criterion in `docs/migration-runbook.md` line 36 — "7 consecutive days of voice replies referencing yesterday's conversation correctly via Hermes session DB recall" — has not been measurable because the personal gateway has not produced traffic. Phase 1 has not started. The "in flight" status row in STATUS.md is fictional.

This explains everything else: G1 baseline cannot fire on `personal-baseline/` because there is no `personal/` traffic pattern to baseline against.

### §1.1 Hermes session storage is `state.db`, not `sessions/*.db`

The earlier G2 Phase 2 plan referenced "SQLite session DBs at `~/.hermes/sessions/`." Reality: Hermes writes to `~/.hermes/state.db` (root, schema includes `messages` + `sessions` tables) AND per-profile `~/.hermes/profiles/{slug}/state.db`. Only `atlas-ceo` has a profile-scoped `state.db` (mtime 2026-05-05 16:52, size 100KB — small). The `sessions/` directory is empty and unused. PLAN.md §1 G2 step 2 was based on a wrong directory assumption.

### §1.2 What this means for the next phase

The "7-day window between 4.7.0 cleared and G1 landing" is the wrong frame. There is no G1 to land at the end of it because Phase 1 hasn't produced the traffic G1 baselines against. The actual ladder of dependencies:

1. **Restart Phase 1** — bring the `personal/` gateway up, verify it routes through LiteLLM (after §5.3 Docker green), confirm traffic generates `state.db.sessions` rows
2. **Run Phase 1 for its real shadow window** (acceptance: 7 consecutive days of voice replies with session recall vs gravity-claw transcript baseline)
3. **THEN G1 baseline** captures meaningful Hermes-personal numbers
4. **THEN sub-phase 4.7.1** has a baseline to compare against

Honest reframe: G1 lands when Phase 1 has run for ≥7 nights post-restart. Earliest realistic G1 date: ~2026-05-15+ depending on tonight's restart success. Calendar slips, structure holds. The 4.7.0 commit (`a866abb`) is still correct — design specs, contract tests, ops scripts hold. ADR-006's bare-metal commitment holds. PLAN.md sub-phase sequencing holds.

### §1.3 Other infra gaps (downstream of §1.0; verify post-restart)

| Gap                                                      | Reality                                                                                                                                                                                                                                                  | Impact                                                                                                                                                       |
| -------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `~/.hermes/profiles/personal-baseline/` shadow workspace | Does NOT exist                                                                                                                                                                                                                                           | G1 has no isolated workspace as PLAN.md §1 G1 specifies — runs against canonical `personal/` would pollute live Phase 1 shadow                               |
| `scripts/clone-profile-baseline.sh`                      | Does NOT exist (referenced in our recently-amended PLAN.md G1 step 1)                                                                                                                                                                                    | Cannot bootstrap shadow workspace via documented path                                                                                                        |
| `~/.hermes/sessions/`                                    | Empty (no `.db` files; dir mtime `May 4 13:24`)                                                                                                                                                                                                          | G2 Phase 2 SQLite session-DB tool-call query has no source data; Hermes either writes sessions elsewhere, has not run enough traffic, or schema/path drifted |
| `email-triage-eval-nightly.sh`                           | Loaded into launchd, state `0` (not running). Script measures **email-triage SKU Promptfoo pass-rate across providers** — NOT per-Hermes-profile Ragas faithfulness, latency p95, cost p50/p95, trace volume per 24h that PLAN.md §1 G1 actually demands | The "nightly capture" already wired up does not produce the G1 evidence the gate evaluates against                                                           |
| LiteLLM proxy at `127.0.0.1:4000`                        | Docker daemon down (`Cannot connect to docker.sock`)                                                                                                                                                                                                     | LiteLLM is not currently routing; Hermes profiles cannot make LLM calls if any are scheduled                                                                 |
| Langfuse at `localhost:3200`                             | Not responding                                                                                                                                                                                                                                           | Trace export pipeline is offline; G1's "trace volume per 24h" cannot be measured                                                                             |

These six gaps **gate** any plan that pretends G1 is firing. Closing them is itself the work.

## §2 Architecture Decision (UPDATED PM)

**Chosen approach: RESTART PHASE 1, THEN MEASURE.**

The original frame ("repair G1 readiness in the 7-day window") was based on the assumption that Phase 1 was producing traffic that G1 would baseline. §1.0 disproves that. The corrected ladder:

1. **Restart Phase 1 personal-profile shadow** (today): bring up Docker → LiteLLM → personal gateway via `hermes profile use personal && hermes gateway start`. Send a real Telegram message to the personal bot, confirm Hermes routes the request through LiteLLM, replies, and writes to `state.db.sessions`. End of day: at least one round-trip recorded.
2. **Run Phase 1 for ≥7 consecutive days** of organic personal-bot traffic. Acceptance per `docs/migration-runbook.md` line 36: voice replies referencing yesterday's conversation correctly via Hermes session DB recall, zero cross-talk vs gravity-claw transcript baseline.
3. **Then build G1 capture** against the now-real `state.db.sessions` data. The capture is a small bash + sqlite + curl script per VanClief's folder-first directive — no framework. It emits one row per night to `HERMES_BASELINE.md` with Promptfoo Wilson lower-CI, Ragas faithfulness, cost-per-session p50/p95, p95 latency, trace volume.
4. **Then sub-phase 4.7.1** loop primitive build, gated by token-delta against the now-real baseline.

Everything in §6 (defer list) stays deferred — agency-agents, pre-4.7.1 probe, LAIK lock, compound-rules codification. VanClief's Ladder-of-AI-Failure verdict on agency-agents stands and is now part of this plan as `ladder_test.publishable: false` for raw import; pattern-extraction-only when picked up post-Phase-1.

**Alternatives considered:**

| Alternative                                                                                                                        | Why rejected                                                                                                                                                                                                                                          |
| ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. Maximize the 7-day window**: ship G2 Phase 2 + agency-agents cherry-pick + LAIK lock + throwaway probe in parallel            | Violates ADR-006 spirit; risks polluting G1 baseline; operator-attention bottleneck; architecture lens flags Tier 4 SkillRegistry CRITICAL mismatch with agency-agents shape; risk-assessor rates agency-agents-during-G1 as `defer entirely past G1` |
| **B. Wait for G1, do nothing else**: lock down to Hermes pin, run G1, planning pass post-2026-05-13                                | Skeptic finding 1 endorses this. Rejected on operator-velocity grounds: the G1-readiness repair is itself non-trivial and must fire today, otherwise tonight's first capture night is wasted                                                          |
| **C. Pull Phase 4.5 LAIK lock forward**: own LAIK MCP boundary contract test now to lift dependency from Phase 4.7.1 critical path | First-principles names this; rejected because the lock requires a real Phase 4.5 implementation to contract-test against, and that doesn't exist; locking against mocks creates false confidence                                                      |

**Trade-off summary:** what we gain is clean G1 evidence and an honest baseline; what we give up is the appearance of velocity in this calendar week. Per the session compound entry, calendar-pressure-as-urgency is itself the failure mode this skill exists to prevent.

## §3 Strategic-alignment Q&A (operator's four questions, answered)

The operator's prompt named four strategic-alignment questions. Answers, evidence-bound:

**A. Clear G2 Phase 2 then start 4.7.1 against personal-baseline immediately, or wait for G1 fully?**
Wait for G1. ADR-006's bare-metal commitment is the direction, not a calendar accelerant. The 4.7.1 gate (token delta ≤5% vs Hermes baseline on 30 golden questions) cannot be evaluated without the baseline. Pre-baseline 4.7.1 work is throwaway-with-no-learning-payoff (skeptic finding 3, first-principles finding 3 converge). G2 Phase 2 IS a different kind of work — it's data plumbing not runtime code, and it does not violate ADR-006 — so it can fire IF the source data exists, which pre-flight casts in doubt.

**B. Does agency-agents rise to first-class next phase, or stay 30-min tactical?**
Stay tactical, AND defer past G1 anyway. Three convergent findings:

- Architecture lens CRITICAL: agency-agents heavy-persona shape (150-300 LOC each, emoji+vibe frontmatter) does not map onto either ~/.claude/agents/ minimalist subagent shape (30-50 LOC, tools/disallowedTools schema) OR the Tier 4 SkillRegistry agentskills.io progressive-disclosure format. A naive cherry-pick into either path either silently parses wrong (wrong semantic) or rejects the file entirely.
- Risk-assessor: defer agency-agents past 2026-05-13 entirely; importing during G1 is 0-value and 3-hour cost.
- Supply-chain lens: 222/225 reject ratio + no commit-hash pin + no provenance metadata + heavy prompt-injection surface area = importing 3-7 raw files into ~/.claude/agents/ is a trust-boundary expansion that needs a full ADR, not a 30-min triage.
  The right scope when picked up post-G1 is described in §6 below.

**C. autonomous-optimization-architect spec × LiteLLM stack — adopt as meta-agent?**
Tempting but no, not in this window. The spec aligns thematically with ADR-005 (LiteLLM routing + per-key budgets + circuit breakers + shadow testing) and could in principle operate the 14-day shadow window's tier-cheap defaults. But operationalizing it requires (a) format adapter to map persona→our-runtime, (b) explicit handoff with our existing `ops` profile (which already owns LiteLLM ledger + cap watching per ADR-005), (c) a place to actually run it. Adopting now without those creates a fourth axis (persona-as-prompt-narrative) layered on top of agents/skills/profiles — architecture lens finding 4 specifically warns against this. Recommended path: extract the _patterns_ (circuit breakers, shadow testing, per-call cost ceilings) into the existing `ops` profile's playbook and the LiteLLM admin-API runbook; do NOT import the persona file.

**D. Second-order coupling with PF Runtime sub-phase 4.7.2 SkillRegistry?**
Real risk, architecture-finding-1 CRITICAL: Tier 4 reads `agentskills.io` progressive-disclosure format. Importing agency-agents into either `hermes/profiles/{slug}/skills/` or `~/.hermes/skills/` (shared) leaks heavy persona files into the Tier 4 read path during the 4.7.2 24h soak, which (a) makes skill-novelty thresholds harder to clear (auto-author trigger may never fire) and (b) shifts Ragas faithfulness baseline because the agent's generation distribution changes. Architecture lens recommends: lock Tier 4 read path to profile-local only (NOT shared `~/.hermes/skills/`) before any persona import is even considered. This is a SPEC.md amendment, not a build task; cheap to land in this window if at all.

## §4 Reversibility Ledger

| Plan Step                                                                                  | Class                                | Cost if Wrong                                                              | Recommendation                                                              |
| ------------------------------------------------------------------------------------------ | ------------------------------------ | -------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| §5.1 Bootstrap `personal-baseline/` shadow workspace                                       | TYPE-2                               | Low — `rm -rf` and reclone                                                 | Fast-track                                                                  |
| §5.2 Write `clone-profile-baseline.sh`                                                     | TYPE-2                               | Low — script revert                                                        | Fast-track                                                                  |
| §5.3 Confirm Docker/LiteLLM/Langfuse running OR document offline impact on G1              | TYPE-2                               | None — observation                                                         | Fast-track                                                                  |
| §5.4 Wire per-profile G1 capture script (5 metrics PLAN.md names)                          | TYPE-2                               | Low — script revert; no production state                                   | Extra diligence on metric definitions; mock-fixture-validate before night 1 |
| §5.5 Audit `~/.hermes/sessions/` shape; if empty, downgrade G2 path                        | TYPE-2                               | None — STATUS.md edit                                                      | Fast-track                                                                  |
| §5.6 G2 Phase 2 SQLite + Langfuse query (CONDITIONAL on §5.5 finding session DBs)          | TYPE-2                               | Low — read-only script + fixture-test                                      | Build only IF source data exists; otherwise document and DEFER              |
| §5.7 SPEC.md amendment locking Tier 4 read path to profile-local                           | TYPE-1 (soft)                        | Low — SPEC edit + Codex re-review                                          | Worth doing this window — closes architecture-finding-1 cheaply             |
| §5.8 Pause `email-triage-eval-nightly` during 2026-05-06→2026-05-13 OR scope it explicitly | TYPE-2                               | Low — re-enable                                                            | Fast-track per concurrency lens finding 2                                   |
| §6 agency-agents triage (DEFERRED to post-G1)                                              | TYPE-2 with mental-model TYPE-1 risk | Reverting an import after operator forms a mental model is socially TYPE-1 | Defer; when picked up, scope per §6                                         |
| §7 pre-4.7.1 throwaway probe (DEFERRED)                                                    | TYPE-2 ephemeral                     | Conditional 4-6hr loss if G1 reveals different bottleneck                  | Defer until G1 lands                                                        |
| §8 LAIK MCP lock (DEFERRED)                                                                | TYPE-1 (status flip)                 | Re-DRAFT carries social cost                                               | Defer until Phase 4.5 implementation exists to contract-test against        |
| §9 Compound-rules codification (DEFERRED)                                                  | TYPE-1 (CARL/hook/CLAUDE.md)         | Coupling cost across projects                                              | Defer; memory entries hold for now                                          |

## §5 Implementation Strategy — Phase 1: Repair G1 readiness (Day 1, today/tonight)

This is THE deliverable for the 7-day window. Everything else is conditional on these landing.

### §5.1 Bootstrap `~/.hermes/profiles/personal-baseline/` shadow workspace

```bash
# Create the workspace by mirroring canonical personal/ profile
cp -R ~/.hermes/profiles/personal ~/.hermes/profiles/personal-baseline

# Mint a separate LiteLLM API-key alias so cost/trace metrics don't comingle
# (This requires LiteLLM to be running — see §5.3)
litellm-cli key create --alias personal-baseline-tier-cheap --tier cheap \
  --max-budget 7 --max-budget-per-day 0.30
# (or wait until LiteLLM is up if down, see §5.3)

# Verify validate-profile still passes against the cloned dir
~/Projects/agents/scripts/validate-profile.sh personal-baseline
```

LOC estimate: 0 production code; 1 shell command sequence; ~10min.

**Acceptance:** `python3 tests/profile_dir_contract.py` reports PASS for `personal-baseline` (current contract test passes 13/13; this would make 14/14).

### §5.2 Write `scripts/clone-profile-baseline.sh`

Bash script that wraps the §5.1 sequence so future shadow workspaces (e.g., for Phase 4.7.4 mid-pilot on `atlas-ceo` per PLAN.md §10 pilot-ladder) reuse the same path.

```bash
# scripts/clone-profile-baseline.sh
# Usage: clone-profile-baseline.sh <source-profile> <target-baseline>
# - Copies the source profile dir to a sibling baseline dir
# - Mints a separate LiteLLM key alias for the baseline
# - Creates a separate Langfuse project tag for the baseline
# - Runs validate-profile.sh against the result
```

LOC estimate: ~80 LOC bash + tests/clone-profile-baseline.test.sh. ~30min.

**Acceptance:** Running `./scripts/clone-profile-baseline.sh personal personal-baseline` reproduces the §5.1 result deterministically.

### §5.3 Confirm Docker / LiteLLM / Langfuse runtime state

```bash
# Probe each
open -a Docker             # if down, requires user keystroke
docker ps --filter name=litellm
curl -fsS http://127.0.0.1:4000/health
curl -fsS http://localhost:3200/api/public/health
```

**Possible outcomes and gates:**

| State                                   | Action                                                                                                                                    |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| All three up                            | Proceed to §5.4                                                                                                                           |
| Docker down + Alex consents to bring up | `open -a Docker`, wait, retry probes                                                                                                      |
| Docker down + Alex defers               | Halt this plan; G1 cannot fire without LiteLLM routing per ADR-005 + cannot trace per Langfuse — reschedule G1 calendar                   |
| LiteLLM container missing               | `cd ~/.hermes/litellm && docker compose up -d` per ADR-005 §components                                                                    |
| Langfuse missing                        | Investigate per VPS port registry (port 3200 is Caddy-fronted; container at `~/Projects/...`); flag as separate ticket if not on this Mac |

**Acceptance:** `curl http://127.0.0.1:4000/health` returns 200 AND Langfuse trace endpoint returns 200, OR plan is halted with explicit halt-reason note in STATUS.md.

### §5.4 Wire per-profile G1 capture loop

The existing `email-triage-eval-nightly.sh` measures the email-triage Promptfoo SKU pass-rate across providers — useful but NOT what PLAN.md §1 G1 demands. PLAN.md G1 requires **per-profile** capture of: Promptfoo Wilson lower-CI per profile, Ragas faithfulness per profile, cost-per-session p50/p95, p95 latency, trace volume per 24h. Two paths:

**Option A: Author a new `scripts/g1-baseline-capture.sh`** that runs nightly during the 7-night window, iterates 13 profiles (or starts with `personal-baseline` only and expands), runs the existing 30-question golden set per profile, and writes one row per profile per night to `.planning/phase-4-7-prettyfly-runtime/baseline/HERMES_BASELINE.md`. Calls Promptfoo + Ragas + reads Langfuse trace API + reads LiteLLM `/spend/logs` API.

**Option B: Scope G1 down** to `personal-baseline` only for night 1, prove the capture loop end-to-end on one profile, then expand to remaining 12 profiles as the week progresses if the loop is stable.

Recommendation: **Option B** — Karpathy ladder applies inside this prep work too. Throwaway-version-first: night-1 single-profile capture against `personal-baseline`, prove all 5 metrics emit a sane row, then scale.

LOC estimate: ~150 LOC bash + ~50 LOC Python helper for Ragas integration. ~3 hours.

**Acceptance gate (night 1):** `HERMES_BASELINE.md` contains a row with non-empty values for all 5 metric columns for `personal-baseline`, and the row passes a sanity check (Ragas in [0.0, 1.0], cost > 0, latency p95 finite).

### §5.5 Audit `~/.hermes/sessions/` shape; document G2 path

Investigate why `~/.hermes/sessions/` has no `.db` files despite Hermes v0.12.0 being pinned and Phase 1 personal-profile shadow being declared "in flight" since 2026-05-04. Three hypotheses:

1. Hermes writes session state to a different path (config drift; check `~/.hermes/config.yaml` `sessions_dir` setting)
2. Hermes hasn't actually been started; Phase 1 shadow window has been measured against another runtime (gravity-claw?) without the Hermes side ever running
3. Hermes session DB schema changed between probe expectations and reality

LOC estimate: 0 — investigation only. ~30min.

**Acceptance:** STATUS.md row for G2 reflects the actual evidence path. Three outcomes:

- If session DBs exist elsewhere: G2 Phase 2 SQLite work proceeds (§5.6)
- If Hermes hasn't run: surface as a separate finding to operator; Phase 1 shadow window status itself is in question
- If schema changed: document, defer G2 Phase 2 until schema is reconciled

### §5.6 G2 Phase 2 evidence — SQLite + Langfuse trace queries (CONDITIONAL on §5.5)

Only fire if §5.5 finds usable session DBs AND Langfuse trace data exists. Otherwise downgrade G2 status from PARTIAL to "Phase 1 only — sub-phase 4.7.2 feature-scoping decisions ride on config-grep evidence alone, with explicit acceptance of that limitation in PLAN.md §8 risks."

If conditions are met, extends `scripts/hermes-feature-audit.sh` with:

- SQLite query per profile: `SELECT tool_name, COUNT(*) FROM tool_calls WHERE timestamp > now() - 30d GROUP BY tool_name` (schema TBD per §5.5 finding)
- Langfuse trace API query per profile: 80th-percentile-used tools over 30 days
- Combined output appended to `HERMES_FEATURE_USAGE.md` as "Phase 2 evidence" section

LOC estimate: ~120 LOC bash/python. ~3 hours.

**Acceptance:** `HERMES_FEATURE_USAGE.md` contains both Phase 1 (config-grep) and Phase 2 (runtime usage) sections with all 13 profiles. Cross-checks pass (e.g., a profile with non-zero memory_tool runtime calls also has memory_tool=Y in Phase 1 grep).

### §5.7 SPEC.md amendment — Tier 4 profile-local lock

Closes architecture-finding-1 CRITICAL. Amends `pf-runtime/SPEC.md` Memory tier interfaces section + `pf-runtime/docs/MEMORY_LIFECYCLE.md` to specify:

> **Tier 4 read path (HARD CONTRACT).** `SkillRegistry` reads from `~/Projects/agents/hermes/profiles/{slug}/skills/` ONLY. The shared `~/.hermes/skills/` path is deferred to Phase 5+ (marketplace skill distribution). During Phase 4.7 the SkillRegistry MUST NOT cross profile boundaries; per-profile skill_gen_autonomy bounds (per `SKILL_SELF_GEN_BOUNDS.md`) are enforced at this contract.

Plus a contract test `tests/tier4_isolation.py`: assert `SkillRegistry` enumerates only files under `profiles/{slug}/skills/`, never crosses into shared paths.

LOC estimate: ~30 LOC SPEC.md edit + ~80 LOC test. ~45min.

**Acceptance:** Codex re-review on the SPEC amendment + `python3 tests/tier4_isolation.py` PASS.

### §5.8 Pause or scope `email-triage-eval-nightly` during G1 window

Concurrency lens finding 2: the existing nightly job consumes LiteLLM quota that would skew G1's cost-per-session and trace-volume baseline measurements. Three options:

| Option         | Action                                                                                                           | Cost                                                    |
| -------------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Pause launchd  | `launchctl unload ~/Library/LaunchAgents/com.prettyfly.email-triage-eval-nightly.plist` for 7 days               | 7 nights of email-triage drift; need re-enable reminder |
| Tag exempt     | Add `_test_exclude` LiteLLM metadata tag to email-triage calls; G1 capture filters them out                      | ~30min one-line edit; preserves email-triage rhythm     |
| Scope explicit | Document that G1 baseline EXCLUDES email-triage-eval traffic and the cost-per-session metric is "post-exclusion" | 0 cost; 1 STATUS.md note                                |

Recommendation: **Tag exempt** — preserves both rhythms with minimal coupling.

LOC estimate: ~10 LOC edit to `email-triage-eval-nightly.sh`. ~15min.

**Acceptance:** Pre-G1 night-1 capture run shows zero email-triage trace lines in the personal-baseline LiteLLM spend log.

## §6 What we DEFER and how each is scoped when picked up

This section makes the "do not do" decisions explicit so they don't drift back in.

### §6.1 agency-agents cherry-pick (DEFER until ≥2026-05-14)

**When picked up, scope:**

1. NOT a /planning-stack invocation — this is a `/ci-ingest` task with verdict ADD-selective per the existing pipeline. One row added to `~/Projects/memory-vault/continuous-improvement/INDEX.md`, with the per-persona detail in a sibling ADR.
2. Cherry-pick **3 candidates maximum**, audited line-by-line for prompt-injection / external URL / memory-vault references before ANY copy:
   - `engineering-autonomous-optimization-architect.md` — pattern source for ops profile playbook (NOT raw import)
   - `engineering-email-intelligence-engineer.md` — pattern source for email-triage SKU evolution
   - `specialized/agents-orchestrator.md` — pattern source for /build-stack orchestration loop
3. Output is **patterns extracted into existing artifacts**, not new files in `~/.claude/agents/`:
   - Circuit-breaker + cost-ceiling patterns → `~/.claude/references/litellm-cost-defenses.md` (new) or appended to ADR-005
   - Email-pipeline structural-chaos patterns → `marketplace/manifests/email-triage/SKU-evolution-notes.md`
   - Pipeline orchestration patterns → reviewed against `/build-stack` skill, with deltas applied as skill edits
4. Source pinned by commit hash in the ADR header: `agency-agents@<commit>` so future re-syncs are reviewable diffs not surprise updates.
5. ZERO files copied raw into `~/.claude/agents/` — that path stays minimalist (9 curated agents). Heavy persona-narrative shape goes through Hermes profiles if it goes anywhere.
6. Tier 4 SkillRegistry isolation contract (§5.7) lands BEFORE step 1 above so even an accidental import cannot leak across profiles.

**Estimated work post-G1:** ~3 hours (audit + ADR + pattern extraction). One commit when complete.

### §6.2 Pre-Phase-4.7.1 throwaway probe (DEFER until ≥2026-05-13 + G1 numbers in hand)

**When picked up, scope:** ONE 90-minute spike informed by G1's actual numbers. If G1 reveals the bottleneck is somewhere other than the loop primitive (memory tier, channel adapter, MCP latency), the probe target shifts and we save the throwaway cost. If G1 confirms loop primitive is the right thing, then build to `personal-baseline/` per PLAN.md §7 — this is exactly the original Karpathy-ladder cadence.

### §6.3 Phase 4.5 LAIK MCP lock (DEFER until real Phase 4.5 implementation exists)

**When picked up, scope:** the lock is a status change AFTER `tests/laik_mcp_contract.py` runs green against a real LAIK implementation, not against mocks. Phase 4.5 has not started its build yet (per migration runbook); the lock is downstream of that build. For this window, SPEC.md stays DRAFT — that IS the safety net per the fix-then-ship session compound entry. No-op the lock task.

### §6.4 Compound-rules codification (DEFER to Phase 5 hygiene window)

**When picked up, scope:** four memory-vault feedback entries from this session's compound (`feedback_pre_greenlight_audit_design.md`, `feedback_bash_pipefail_in_command_substitution.md`, `feedback_mcp_tenant_scoped_security_pattern.md`, `feedback_multi_doc_sync_not_paraphrase.md`) become candidates for env-level enforcement (CARL rule additions, Stop-hook additions, CLAUDE.md updates). Each requires its own design — which one warrants a hook (deterministic mechanical check) vs which one stays a memory entry (judgment-required guidance). First-principles lens correctly identified these as "Phase 5 hygiene" not "blocking work for Phase 4.7."

### §6.5 personal-baseline source-of-truth re-version (DEFER until 4.7.4 A/B work needs it)

**Added 2026-05-06 PM** via the post-fix swarm. The runtime workspace at `~/.hermes/profiles/personal-baseline/` was cloned from `personal/` during Phase 4.7.0 and now holds the schema-fixed config we landed in commit `55931ae`. There is currently NO source-of-truth at `~/Projects/agents/hermes/profiles/personal-baseline/` — `sync-profile.sh push personal-baseline` would fail with `SRC missing`.

**Why defer:** The skeptic perspective (5th finding, 2026-05-06 PM swarm) flagged that committing the workspace to git now stages measurement scaffold as a runtime artifact. `personal-baseline` is reserved for sub-phase 4.7.4 mid-pilot A/B (per PLAN.md §10 pilot ladder). Until that ladder fires, the workspace is throwaway-style infrastructure — committing it stages git rot.

**When picked up:** post-G1-reframe Codex re-review clears + sub-phase 4.7.4 begins, this becomes a one-commit re-version (`cp -R ~/.hermes/profiles/personal-baseline ~/Projects/agents/hermes/profiles/personal-baseline`, scrub anything secret, commit, then sync-push works). Estimated work: ~30min when picked up.

**No-op for this window.** Runtime mirror has the schema fix; Phase 4.7's gate-decisions don't require source-of-truth parity.

## §7 Risk Assessment

| ID  | Risk                                                                                                                                                                               | Severity | Likelihood | Mitigation                                                                                                                                                     |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | G1 night-1 capture fails because §5.4 capture script has a metric-emission bug; loses 1/7 of the evidence window                                                                   | High     | Medium     | §5.4 mock-fixture-validate the script before scheduling; emit + sanity-check the row interactively first night before relying on launchd                       |
| R2  | `~/.hermes/sessions/` truly empty because Hermes never ran in Phase 1 — meaning Phase 1's "in flight" status is fiction                                                            | High     | Medium     | §5.5 investigation; if true, escalate to operator immediately as a Phase-1-status finding, not a G2 finding                                                    |
| R3  | Docker / LiteLLM / Langfuse runtime brought up under time pressure introduces config drift that pollutes G1 baseline                                                               | Medium   | Medium     | §5.3 explicit health probe with documented green-state; STATUS.md captures the runtime versions and config hashes at G1 start                                  |
| R4  | Operator interrupts G1 capture mid-week to do agency-agents triage anyway because "it's only 30 minutes"; calendar-pressure-as-urgency rationalization                             | Medium   | Medium     | §6.1 explicit defer-until-2026-05-14 documented here; this PLAN.md is the contract                                                                             |
| R5  | SPEC.md Tier 4 amendment (§5.7) introduces a backwards-incompatible change to MEMORY_LIFECYCLE that ripples into PLAN.md §8 sub-phase 4.7.2 expectations                           | Low      | Low        | Codex re-review on the amendment; cross-doc sync grep per session compound rule "multi-doc sync not paraphrase"                                                |
| R6  | Email-triage exclusion (§5.8) misconfigured — exclusion tag silently fails and email-triage spend leaks into G1 cost numbers                                                       | Medium   | Medium     | §5.8 night-1 manual sanity check on `LiteLLM /spend/logs` filtered by exclusion tag                                                                            |
| R7  | Phase 1 personal-profile shadow window (live) makes some change during the G1 capture week (operator-driven message, profile config edit) that drifts the baseline                 | Low      | High       | §5.1 establishes `personal-baseline/` as the isolated workspace specifically to insulate G1 from live-profile drift; live `personal/` continues unchanged      |
| R8  | Architecture-finding-1 (Tier 4 mismatch) silently survives because §5.7 amendment slips the window                                                                                 | Medium   | Medium     | §5.7 is in this window's deliverable list; track it as an explicit acceptance criterion                                                                        |
| R9  | Hidden coupling between PF Runtime sub-phase 4.7.2 design (already shipped in commit a866abb) and the Tier 4 amendment requires a follow-up Codex review on the _combined_ surface | Low      | Medium     | §5.7 acceptance includes Codex re-review; if Codex flags new coupling, add follow-up to STATUS.md                                                              |
| R10 | Operator runs `hermes update` during the window because the commit-watcher daily digest tempts them — breaks the Hermes pin                                                        | Low      | Low        | ADR-006 already documented; commit-watcher emits "do not pull" notice; one-line `alias hermes='echo PINNED'` is cheap belt-and-suspenders if operator wants it |

## §8 ROI Snapshot (for items in §5; deferred items in §6 carry value but no in-window cost)

| Item                                          | Build Hours    | Unlocks                                                                             | Value $ (operator @ $150/hr)                         | Rank             |
| --------------------------------------------- | -------------- | ----------------------------------------------------------------------------------- | ---------------------------------------------------- | ---------------- |
| §5.1+5.2 Shadow workspace + clone script      | 0.7            | G1 capture isolation; reusable for atlas-ceo mid-pilot in PLAN.md §10               | $400-800 (avoided rework on isolation contamination) | 1                |
| §5.4 Per-profile G1 capture loop              | 3              | The actual G1 evidence the gate evaluates against; without this, G1 is unverifiable | $1500-3000 (5-gate cutover decision quality)         | 2                |
| §5.7 Tier 4 profile-local lock SPEC amendment | 0.75           | Closes architecture-finding-1 CRITICAL before sub-phase 4.7.2 build starts          | $600-1200 (avoided 4.7.2 rework)                     | 3                |
| §5.5 Sessions DB audit                        | 0.5            | Honest G2 status; Phase 1 status reality-check                                      | $300-600 (decision quality)                          | 4                |
| §5.6 G2 Phase 2 (CONDITIONAL)                 | 3              | Sub-phase 4.7.2 feature-scoping evidence                                            | $300-1500 (only if §5.5 finds source data)           | 5                |
| §5.3 Runtime probes                           | 0.25           | Foundation; gates everything else                                                   | Forces §5.4-5.6 to be real not fictional             | 0 (table stakes) |
| §5.8 Email-triage exclusion                   | 0.25           | G1 baseline integrity                                                               | $100-200 (avoided budget pollution)                  | 6                |
| **Total in-window cost**                      | **~8.5 hours** |                                                                                     | **~$3K-7K value**                                    |                  |

BATNA: doing nothing produces a fictional G1 row from `email-triage-eval-nightly.sh` that would corrupt the 4.7.5 cutover gate criterion baseline; that's a $10-50K downstream re-baseline cost.

## §9 Adversarial Threat Surface

Top kill chains for this 7-day window:

1. **Operator-self-confusion attack** — operator believes G1 is firing per the existing nightly job because launchd state shows the job loaded; doesn't notice the metric mismatch; signs off on a fake baseline. Mitigation: §5.4 acceptance gate (sanity-check the night-1 row interactively before trusting the loop).
2. **Calendar-pressure rationalization** — operator imports agency-agents anyway under the rationalization "it's reversible," forming a mental model around the 3-7 imports that becomes hard to unwind. Mitigation: §6.1 contract documented in this PLAN; reading this PLAN before any /ci-ingest invocation on agency-agents.
3. **Trust-boundary expansion via persona import** — supply-chain lens flagged: 225 third-party .md files into `~/.claude/agents/` is a global-session influence vector. Mitigation: §6.1 contract specifies pattern-extraction NOT raw import; zero files into `~/.claude/agents/`.
4. **Pin-break by commit-watcher temptation** — operator sees a security-tagged Hermes upstream commit and runs `hermes update` to "be safe." Mitigation: ADR-006 already specifies manual-port-only; STATUS.md week-1 review confirms no upstream pulls.

## §10 3am Test (observability)

If on-call gets paged at 3am during this window:

| Scenario                                                                          | What fires                              | What on-call sees                                       | What's missing → ADD                                                                                                                                              |
| --------------------------------------------------------------------------------- | --------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1 night-1 capture row missing from `HERMES_BASELINE.md` next morning             | No alert (silent miss)                  | nothing                                                 | **ADD:** §5.4 capture script writes `_status` row to a separate file; pre-flight check at `09:00 ET` next-morning launchd job emails operator if `_status` ≠ "ok" |
| Phase 1 personal-profile shadow stops exchanging messages during G1 week          | Hermes profile heartbeat absence        | nothing — current profile-status monitoring is informal | **ADD:** existing `forge-audit` profile already tracks per-profile health; verify `personal/` heartbeat is in scope and alerts go somewhere visible               |
| LiteLLM container OOM-kills mid-capture night                                     | Docker daemon log only                  | docker ps shows missing container next morning          | **ADD:** `~/Library/LaunchAgents/com.prettyfly.litellm-keepalive.plist` health check every 5min, restart on absence                                               |
| Langfuse trace export pipeline backlog grows                                      | Langfuse internal alert (if configured) | unclear without checking dashboard                      | **ADD:** confirm Langfuse `/api/v1/health` is being curl-probed in §5.3 and that probe is repeated daily                                                          |
| Tier 4 amendment regression — sub-phase 4.7.2 work later assumes shared path read | sub-phase 4.7.2 build-time error        | when 4.7.2 fires (weeks away)                           | **ADD:** §5.7 contract test in CI so any future PR that breaks the isolation surface fails review                                                                 |

## §11 Operability Plan

- **Rollback granularity:** all in-window changes are file edits + script additions + STATUS.md updates. Per-step git revert is trivial.
- **Blast radius:** zero production blast radius. Phase 1 personal-profile shadow runs against canonical `personal/`, untouched by `personal-baseline/`.
- **Failure modes catalogued:** §7 risk register R1-R10. Most likely failure is R1 (capture script bug on night 1); recovery is 30min script fix + manual night-1 backfill.
- **Runbook delta:** `docs/migration-runbook.md` Phase 4.7 phase-pointer line gets one update at end-of-window: "G1 capture week complete (nights 1-7) — see HERMES_BASELINE.md."

## §12 Test Strategy

| Item                            | Golden-path test                                                                                 | Layer                      | Intentionally NOT tested                                                        |
| ------------------------------- | ------------------------------------------------------------------------------------------------ | -------------------------- | ------------------------------------------------------------------------------- |
| §5.1 Shadow workspace bootstrap | `tests/profile_dir_contract.py` reports 14/14 PASS                                               | integration (existing)     | LiteLLM key minting fails — that's separate §                                   |
| §5.2 clone-profile-baseline.sh  | shellcheck PASS + idempotency test (run twice, second is no-op)                                  | unit                       | network-failure on LiteLLM key mint (manual fallback)                           |
| §5.4 G1 capture loop            | mock-fixture night-0 dry-run emits a sane row to `HERMES_BASELINE.md.fixture`                    | integration                | actual LLM cost attribution accuracy beyond ±5%                                 |
| §5.6 G2 Phase 2 (if fires)      | static SQLite fixture of 100 mock tool-calls; aggregation matches hand count                     | unit + fixture-integration | 30-day window statistical significance with low-traffic profiles                |
| §5.7 Tier 4 lock                | `tests/tier4_isolation.py` enumeration assertion                                                 | unit                       | Tier 4 actual loader behavior at runtime (deferred to sub-phase 4.7.2 24h soak) |
| §5.8 Email-triage exclusion tag | night-1 LiteLLM /spend/logs filtered by tag — zero email-triage rows in personal-baseline window | integration                | fall-through if tag is silently dropped by LiteLLM (audit logs would catch)     |

Golden path for the WEEK: at end of 2026-05-13, `HERMES_BASELINE.md` contains 7 nights × 1+ profile rows with non-empty 5-metric values, sanity-bounded, and operator can ask "what's the per-profile Ragas distribution this week" and get an answer from the file.

## §13 Verification (end-of-week acceptance)

- [ ] `~/.hermes/profiles/personal-baseline/` exists and `tests/profile_dir_contract.py` reports 14/14 PASS
- [ ] `scripts/clone-profile-baseline.sh` exists, has unit tests, idempotent
- [ ] Docker / LiteLLM / Langfuse runtime probes are 200 OK at G1 night-1 start AND 7 nights later
- [ ] `HERMES_BASELINE.md` contains ≥7 rows (one per night) for at least `personal-baseline`; bonus if scaled to all 13 profiles
- [ ] G2 status in STATUS.md reflects honest evidence: either "Phase 2 complete" (if §5.6 fired green) or "Phase 1 only — Phase 2 deferred per session-DB absence" (with operator acknowledgment)
- [ ] `pf-runtime/SPEC.md` + `MEMORY_LIFECYCLE.md` Tier 4 amendment landed; `tests/tier4_isolation.py` PASS
- [ ] STATUS.md updated with "post-Phase-4.7.0 7-day window: complete" and a dated row pointing here
- [ ] Zero changes in `~/.claude/agents/` (agency-agents stays untouched)
- [ ] Zero new files in `pf-runtime/` (loop primitive build did not start; ADR-006 spirit preserved)
- [ ] G1 actual numbers are in hand to inform the post-G1 planning pass

## §14 Post-G1 (Day 8+) — what fires after this plan completes

In rough priority order, informed by what G1 actually shows:

1. **Read the baseline numbers.** If Hermes Ragas <0.80, halt per PLAN.md §13 no-go criterion — the issue is upstream of runtime choice. If Ragas 0.80-0.85, sub-phase 4.7.2 gate becomes "match Hermes ±0.02 AND clear 0.80 floor." If Ragas ≥0.85, gate is "match ±0.02."
2. **Pick sub-phase 4.7.1 throwaway probe target** based on G1's revealed bottleneck. ~90min spike.
3. **Cherry-pick agency-agents** per §6.1 scope. ~3 hours, /ci-ingest path.
4. **Phase 4.5 LAIK MCP build (not lock)** — start the actual implementation if Phase 4.5 is the next runbook phase. The lock follows the build by definition.
5. **Compound-rules codification candidates** — probably not yet; reassess at Phase 5 hygiene window.

## §15 Confidence

- **High** (90%+) on §1 pre-flight findings (probes are deterministic).
- **High** (85%+) on the recommendation to defer agency-agents past G1 (3 perspectives + supply-chain lens converge).
- **Medium** (70-80%) on §5.4 capture script LOC estimate (depends on Promptfoo + Ragas + Langfuse API shapes; could surprise either direction).
- **Medium** (75%) on §5.5 finding usable session DB evidence (could find Hermes never ran; that's a separate operator surfacing).
- **High** (90%) on §6 deferrals (cross-cutting findings #1, #2, #3 from specialist board converge with first-principles + risk-assessor).

---

## Planning Stack Report

```
Mode: TECH
Depth: --deep
Confidence: Medium-High (85%)
Sources: codebase (10 files read), memory (vault wiki + ideas memo + compound),
         existing plans (PLAN.md + STATUS.md + ADR-006 + ADR-005 + runbook),
         research (skipped — sufficient prior context),
         best-practices (skipped — sufficient prior context),
         live pre-flight probes (6 environment checks)
Perspectives (5): skeptic ✓, architecture ✓ CRITICAL Tier 4 finding,
                  first-principles ✓, risk-assessor ✓, pattern-matcher ✓
Specialist Lenses (--deep): 5 always-on (adversary, observability,
                            reversibility, economist, test-strategist)
                           + 2 keyword-gated (supply-chain, concurrency)
                           = 7 fired
Cross-cutting findings: 4 (agency-agents trust-boundary, conditional-value
                          deferrals, G2 Phase 2 high ROI, email-triage
                          contention)
Verification: 1 pass
Prior decisions applied: ADR-001, ADR-005, ADR-006, six locked operator
                         commitments, Phase 4.7 PLAN.md, session compound
                         rules
Est. cost: ~$0.40 (5 perspectives + 1 specialist board on haiku)
```

**Awaiting operator confirmation before any /commit.**
