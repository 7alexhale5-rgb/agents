# PF Runtime failure modes (top-10 catalog)

**Status**: DRAFT (Phase 4.7.0 closeout). Becomes the seed for every alert in PLAN §12 and the precondition for the 4.7.5 cutover review (PLAN §13).
**Source material**: PLAN.md §5 risk register, MEMORY_LIFECYCLE.md failure-mode notes, ADAPTER_PLUGIN_INTERFACE.md reconnect contract, NEXT_PHASE_PLAN.md §1.3 + §7 risk additions, the four named in this swarm review (skill auto-author runaway, LAIK token expiry, gateway crash mid-stream, loop deadlock), SQLite WAL corruption under 13-profile concurrent write.

## How to read this doc

Each mode lists: **(severity)** how bad if it fires; **(likelihood)** how often expected; **(owner)** who designs the mitigation; **(detection signal)** the trace/log/event that fires when this happens; **(mitigation)** what we already have or need to add.

Modes are ordered by `severity × likelihood`, not alphabetically. M1 is the most operationally important; M10 is the least.

---

## M1. Skill auto-author runaway feedback loop

**Severity**: HIGH — runaway burns budget AND poisons memory tier with junk skills that propagate across 13 profiles.
**Likelihood**: MEDIUM — only requires a self-reinforcing skill-novelty signal (e.g. an inbound message asking "do you have a skill for X?" makes the system author X, then asks itself again next turn).

**Owner**: SKILL_SELF_GEN_BOUNDS.md is the contract surface.

**Detection signal**: `skill_self_gen.candidate_count` per profile per 72h-rolling-window exceeds the configured cap; `skill_self_gen.author_attempt` events fire faster than 1 per hour over a 12h window.

**Mitigation**:

- Existing: cap quantity (≤3/72h), size (≤100 LOC), operator approval for non-personal profiles.
- **Added in §5.9.2**: code-bearing candidates require operator approval regardless of profile.
- Add: `mutation_audit.candidate_quality_score` from a tier-cheap LLM judge; auto-rejected candidates with score <0.3 do not count toward the 3/72h cap (otherwise an attacker can drain the budget with junk to block legitimate self-gen).

---

## M2. LAIK session-token expiry mid-mutation-proposal

**Severity**: HIGH — half-applied mutation produces inconsistent tenant state.
**Likelihood**: LOW (token TTL is operator-controlled) but inevitable at the boundaries.

**Owner**: LAIK MCP SPEC §6 (`session_token` JWS).

**Detection signal**: `tool.error_class=auth` with `tool.name=laik.mutation_apply` AND a successful `laik.mutation_propose` for the same proposal_id within the previous TTL window.

**Mitigation**:

- LAIK MCP wraps every `mutation_apply` in a transaction; partial application rolls back on any auth failure mid-call.
- Adminial UI re-issues approval token AFTER `mutation_propose` returns proposal_id; the proposal is held server-side with its own TTL longer than the session token's TTL. The propose→approve→apply chain decouples token lifetimes.
- Add: nightly job reconciles `mutation_proposals` table — any proposal in state `applying` for >5min is force-rolled-back and surfaced as an incident.

---

## M3. Profile gateway crash mid-streaming-response

**Severity**: HIGH — user sees a partial reply, no clear "I'm thinking" indicator that the back-end died. Trust erosion.
**Likelihood**: MEDIUM — every long-running tool call (e.g. an Obsidian search across 50K notes) is exposed to OOM, network hiccups, model rate limits.

**Owner**: ADAPTER_PLUGIN_INTERFACE.md `reconnect` contract; channel-adapter heartbeat.

**Detection signal**: `sessions.ended_at IS NULL` for >5 minutes AND `sessions.message_count > 0` (started streaming but never closed). launchd `KeepAlive` restarts the gateway, but the orphaned session row needs detection.

**Mitigation**:

- launchd `KeepAlive` restarts the gateway plist on crash. Already configured for `personal` (PID 36297 was launchd-started today).
- Channel adapter posts a `[stream interrupted — retry?]` user-visible message when reconnecting to an orphaned session.
- Sweep job: any `sessions` row open >5min closes with `end_reason=orphaned`. Aggregate count alerts when >1% of daily sessions orphan.

---

## M4. Loop primitive deadlock on self-referential tool call

**Severity**: HIGH — burns budget until the iteration ceiling fires; user waits indefinitely.
**Likelihood**: MEDIUM in early 4.7.1 builds; LOW once the loop primitive matures.

**Owner**: SPEC.md §loop primitive, `pf_runtime/runtime/loop.py` (when it exists).

**Detection signal**: `pf_runtime.span_kind=loop_iteration` count for a single `pf_runtime.session_id` exceeds the configured iteration_budget (`personal/config.yaml: max_iterations: 32`).

**Mitigation**:

- Existing: `agent.max_iterations` in profile config caps the loop.
- Existing: `agent.iteration_budget_tokens` caps token spend per session (200K for personal).
- Add: cycle-detection on tool-call argument hashes — if the SAME tool gets called with the SAME args 3 times in one session, halt with `loop_cycle_detected` end_reason.
- Add: streaming heartbeat — every 30s the loop emits a `[still working: tool=X]` channel signal so the user knows it's alive (not the same as a deadlock fix, but reduces UX damage).

---

## M5. SQLite WAL corruption under concurrent profile writes

**Severity**: HIGH — corruption either loses sessions data or makes the DB unreadable, breaking G1 baseline.
**Likelihood**: LOW for 1-3 active profiles; rises sharply at 13.

**Owner**: PF Runtime memory tier writes; ADR-006 §3.7 Kanban Postgres switch addresses Kanban specifically but not the per-profile `state.db`.

**Detection signal**: `sqlite3 ... ".pragma integrity_check"` returns non-OK; or sessions row count drops between two consecutive captures with no `DELETE` in between.

**Mitigation**:

- WAL mode set per profile; `PRAGMA journal_mode=WAL` AND `PRAGMA synchronous=NORMAL` (not OFF).
- Each profile writes to its OWN `state.db` — confirmed by §5.5 audit (no shared state.db writes; root state.db is empty). Already the design.
- Hourly `sqlite3 .backup` to `~/Assets/backups/hermes-state-{slug}-{date}.db`. Per plan §6.1 (gap analysis finding 6.1).
- Schema-version column already present in `state.db.schema_version` table — bump on any breaking change.

---

## M6. Cross-profile contamination via root `state.db`

**Severity**: MEDIUM — currently zero impact (root state.db is empty per §5.5 audit) but a single misconfigured write path opens a tenant-leak vector.
**Likelihood**: LOW today, MEDIUM if PF Runtime introduces any "global" memory write path.

**Owner**: MEMORY_LIFECYCLE.md tier write contracts; plan §5.9.8 cross-profile contamination assertion.

**Detection signal**: `~/.hermes/state.db` row counts for `sessions` or `messages` are non-zero at any G1 capture night start when they were zero at the previous start.

**Mitigation**:

- Existing: §5.5 audit confirmed root state.db is empty.
- §5.9.8 capture-script post-assertion: `COUNT(*) WHERE profile_id='atlas-ceo' AND date=G1_date` unchanged across capture window — fails the night if violated.
- Add: contract test asserting `BufferStore` constructor refuses `profile_slug=None` (per gap analysis 2.1). No "global" write path exists in code — make that policy by code.

---

## M7. LiteLLM key budget exhaustion mid-session

**Severity**: MEDIUM — user gets a 429 mid-conversation; loop primitive must degrade gracefully or session breaks.
**Likelihood**: MEDIUM during evaluation runs (Ragas + Promptfoo costs add up).

**Owner**: ADR-005 (LiteLLM ledger + circuit breakers); plan §6 cost-degradation gap.

**Detection signal**: `tool.error_class=rate_limit` from `llm.provider=litellm` OR direct LiteLLM 429 in `messages.finish_reason=rate_limit_exceeded`.

**Mitigation**:

- Per gap analysis 7.2: on 429 from LiteLLM cap, runtime emits a one-line apology in the channel, marks session `degraded`, halts further LLM calls until next budget window. **No silent tier swap** — silent degradation is worse than user-visible halt.
- §5.1 raises `personal-baseline-tier-cheap` daily cap from $0.30 to $1.00 per the cost-cap math in plan §4.4.
- Add: pre-call cost forecast — if remaining daily budget <2× expected call cost, refuse the call with a clear user-facing message rather than a mid-stream cutoff.

---

## M8. Channel adapter authentication drift (OAuth token rotation, missing scopes)

**Severity**: MEDIUM — Bot stops working but doesn't crash; user sees no replies; if the bot is on autonomous tasks (cron jobs), the operator may not notice for hours.
**Likelihood**: MEDIUM — today the personal gateway is logging `missing_scope: groups:read` every 4 minutes (plan §2.3.1).

**Owner**: ADAPTER_PLUGIN_INTERFACE.md auth contract; per-channel adapter heartbeat.

**Detection signal**: log pattern `missing_scope` count per profile per hour; OR `channel_adapter.heartbeat.last_success_age` exceeds threshold.

**Mitigation**:

- §5.0b explicitly patches `groups:read` for the personal/atlas-ceo Slack apps (operator-driven, 2FA-gated).
- Add: per-adapter heartbeat log; alert when `missing_scope` errors exceed 1/hour for >2h.
- Add: token-rotation runbook in `~/.claude/references/` describing per-channel re-pairing procedure (Slack OAuth, Telegram bot token, etc.).

---

## M9. Hermes upstream commit-watcher false-positive (operator pulls a "security" patch that breaks pin)

**Severity**: MEDIUM — schema change mid-window invalidates G1 baseline (plan R11).
**Likelihood**: LOW per upstream cadence (1 commit per day average) but cumulative over weeks.

**Owner**: ADR-006 manual-port discipline; commit-watcher digest email.

**Detection signal**: `pf_runtime.runtime_commit` attribute on capture script rows changes between two qualifying nights without an explicit ADR amendment.

**Mitigation**:

- Existing: ADR-006 says manual-port-only, never `hermes update`.
- Plan §4.4 Hermes-pin assertion in the capture script row format — every night records the binary's commit hash.
- Plan R11 mitigation: clock resets to night 1 if the pin commit changes mid-window.
- Add: launchd alias suggestion `alias hermes='echo PINNED'` if operator wants belt-and-suspenders against muscle memory.

---

## M10. Tier 4 skill registry leak (cross-profile skill exposure)

**Severity**: MEDIUM — skills authored for one profile leak into another's loader path; behavioral drift hard to diagnose.
**Likelihood**: LOW with §5.7 contract test in place; HIGH without it.

**Owner**: plan §5.7 (Tier 4 isolation contract) + `tests/tier4_isolation.py`.

**Detection signal**: `pf_runtime.skill_slug` attribute on a span shows a slug that does NOT live under `hermes/profiles/{this_span.profile_slug}/skills/`.

**Mitigation**:

- §5.7 SPEC.md amendment locks Tier 4 read path to `profiles/{slug}/skills/` only.
- §5.7 contract test asserts SkillRegistry never enumerates files outside that path.
- §5.9.5 file-shape classifier ensures any new file landing in `hermes/profiles/`, `~/.claude/agents/`, or `~/.hermes/skills/` is correctly typed and isolated.

---

## What's NOT in this list (and why)

- **Network outages** — out of PF Runtime scope; OS-level.
- **Operator distraction** — out of doc scope; covered by `personal/config.yaml: approval.mode=explicit_for_outbound`.
- **Inbound prompt injection** — covered separately in `THREAT_MODEL.md` A1 because it's an attack class, not an operational failure mode. The two docs reference each other; do not duplicate.
- **Eval-script silent failure** — covered in plan §4.4 (right-table assertion, traffic floor, 429 detector, email-triage leak detector, Hermes-pin assertion). Capture script enforces, this doc doesn't.
- **Codex review pipeline drift** — out of scope; lives in `~/.claude/references/code-review-policy.md`.

## Verification

For each mode above, the following must exist before the 4.7.5 cutover:

- [ ] An alert wired in the operator's daily dashboard (or a launchd-driven email) firing on the named detection signal.
- [ ] A runbook entry in `docs/migration-runbook.md` describing operator-side response.
- [ ] A test in `tests/failure_modes/` (where applicable) reproducing the mode and asserting detection.

Until all three columns are green per mode, the mode is DRAFT-mitigated. The 3am test (PLAN §12) requires GREEN on all 10.
