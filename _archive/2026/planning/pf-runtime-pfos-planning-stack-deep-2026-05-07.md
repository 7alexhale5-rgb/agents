---
title: PF Runtime × PFOS — planning-stack deep (QA/QC + integration)
created: 2026-05-07
mode: tech
depth: deep
sources: wiki/memory-vault wiki/prettyfly-os, agents/.planning/phase-4-7-prettyfly-runtime, cursor plan pf-runtime×pfos integration, pf-qa + CI
---

# Technical plan: Full remediation, QA/QC, and seamless PF Runtime × PrettyFly OS integration

## Parsed intent

| Field                  | Value                                                                                                                                                                                      |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **GOAL**               | Bulletproof QA/QC across `pf-runtime` + PFOS integration surfaces; full remediation posture with tests/validations; align with Runtime Playground + Iris-first ADR program                 |
| **MODE**               | **TECH** (CI/CD, schema, API contracts, observability, multi-repo gates)                                                                                                                   |
| **DEPTH**              | **deep** (3 verification passes, reversibility, adversarial + observability, test strategist)                                                                                              |
| **Interview (--deep)** | Compressed from session context: MNESK boundary preserved; vault read path **deferred** until Iris B4 spike; Coach spine-only acceptable; Hermes superseded for PrettyFly operator surface |

---

## Context

### Project

- **Hermes monorepo** ([`~/Projects/agents`](file:///Users/alexhale/Projects/agents)): `pf-runtime` package, `scripts/pf-qa.sh`, `.github/workflows/pf-runtime-ci.yml`, phase 4.7 cutover playbooks.
- **PrettyFly OS** ([`~/Projects/prettyfly-os`](file:///Users/alexhale/Projects/prettyfly-os)): Next.js command surface, `agent_events`, Stage 4 v2 fleet plane, `npm run verify`.

### Current state (relevant)

- **Runtime QA:** [`scripts/pf-qa.sh`](file:///Users/alexhale/Projects/agents/scripts/pf-qa.sh) = ruff + mypy + pytest (cov floor in `pf-runtime/pyproject.toml`) + bandit + pip-audit. CI mirrors with Python 3.11/3.12.
- **PFOS QA:** `npm run verify` = tsc + eslint + vitest + build.
- **Integration contract** (target): typed `agent-event` writeback, optional `SurfaceKind` extension for `pf_runtime`, playground UI replacing `/agents` registry — see expanded plan: `~/.cursor/plans/pf_runtime_×_prettyfly_os_—_integration_plan_(contract-first)_b7cd2da7.plan.md`.
- **Operational lesson (STATUS):** Per-profile `.env` stubs caused missing `OPENROUTER_API_KEY` under launchd; PF Runtime cutover must **repeat the same operator discipline** ([`.planning/phase-4-7-prettyfly-runtime/STATUS.md`](file:///Users/alexhale/Projects/agents/.planning/phase-4-7-prettyfly-runtime/STATUS.md)).

### Prior decisions / wiki

- **PrettyFly OS** (wiki index): command surface, pulse architecture; prod deploy cadence separate from agents repo.
- **PFOS CLAUDE.md**: MNESK + Hermes boundary — PFOS **does not** supervise subprocesses; **contracts + events**.

---

## Architecture decision

### Chosen approach

1. **Two-repo gates are mandatory on main:** `bash scripts/pf-qa.sh` (agents) and `npm run verify` (prettyfly-os) for any slice that touches both.
2. **Single integration spine:** PF Runtime → HTTPS → PFOS `/api/silos/[slug]/agent-event` (existing Stage 4 v2) with **`pf_runtime` surface** after migration — no parallel “shadow ingest” unless ADR revs.
3. **Playground v0** is **read-mostly**: surfaces `agent_events` + links; heavy dispatch stays cmd-K / Slack / VPS until ADR-A defines scope.
4. **Secrets & env:** Document and automate checks that VPS/launchd jobs load **provider keys** the same way as interactive shells (preflight script already partially exists: [`scripts/pf-cutover-preflight.sh`](file:///Users/alexhale/Projects/agents/scripts/pf-cutover-preflight.sh)).

### Alternatives considered

| Alternative                                        | Why not default                                          |
| -------------------------------------------------- | -------------------------------------------------------- |
| PFOS embeds Python / runs gateway as child process | Violates MNESK; duplicates supervision                   |
| Hermes remains UX integration layer for PFOS       | Explicitly superseded by product direction for PrettyFly |
| Service-role Supabase key on runtime host          | Security debt; use scoped bearer / server APIs per ADR-C |
| Skip `pf_runtime` enum; reuse `cli`                | Loses fleet rollup clarity; cheap to add with migration  |

### Trade-offs

- **Gain:** Clear ownership, testable contracts, CI truth on both sides.
- **Cost:** Every surface change needs **Supabase migration + TS enum sync**; operator must maintain **dual env** discipline (VPS + Vercel).

---

## Reversibility ledger

| Plan step                                        | Class  | Irreversibility cost                       | Recommendation                                             |
| ------------------------------------------------ | ------ | ------------------------------------------ | ---------------------------------------------------------- |
| Add `pf_runtime` to `agent_events.surface` CHECK | TYPE-2 | Low — new migration to widen/rollback enum | Ship with migration; avoid reusing enum values             |
| Playground UI replaces `/agents` layout          | TYPE-1 | Low — git revert routes                    | Keep old components in `/_archive` or feature-flag         |
| PF Runtime emits PFOS events                     | TYPE-1 | Low — env toggle off                       | `PFOS_AGENT_EVENT_URL` unset = no-op                       |
| Per-agent GitHub PAT/App                         | TYPE-3 | Medium — token rotation, audit             | Start **read-only**; write behind flag (ADR-D)             |
| Hermes launchd disabled                          | TYPE-3 | Medium — ops prefers rollback plist        | Keep Hermes plist **offline** but documented 30-day window |

---

## ROI snapshot

| Investment                        | Return                                       | Payoff horizon |
| --------------------------------- | -------------------------------------------- | -------------- |
| ~2–4h ADR quartet (paper)         | StopsScope creep on Coach + UI               | Immediate      |
| ~1d `pf_runtime` + ingest + tests | Fleet visibility + coverage gate honesty     | 1 sprint       |
| ~2–3d playground shell            | Operator trust (“see the agent working”)     | 1 sprint       |
| ~1d env/launchd hardening         | Avoids repeat STATUS incident (missing keys) | Immediate      |

---

## Adversarial threat surface (planning-level)

| Threat                                           | Mitigation in plan                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------ |
| Stolen ingest bearer token → spam `agent_events` | Token scoped to write + IP allowlist optional; rate limits on route (PFOS)     |
| Runtime reads vault via leaked service role      | ADR-C forbids; integration tests assert no service key in runtime env          |
| Slack impersonation / wrong workspace            | ADR-B pins workspace + channel IDs; bot token per workspace                    |
| GitHub token over-permission                     | ADR-D allowlist; read before write                                             |
| **launchd PATH/env drift**                       | Extend preflight: assert required keys **present in process** before kickstart |

---

## Observability / 3am test

**At 3am, an operator must answer in <5 min:**

1. Is PF Runtime process up? (`launchctl` / systemd + health log line)
2. Did the last Slack inbound produce an `agent_events` row with `surface=pf_runtime`?
3. Is Sentry quiet for `pf_runtime` + PFOS API route?
4. Can we grep a **single canonical log token** (e.g. `PFRT_GATEWAY_READY`) in journal for fleet-coverage alignment?

If any answer is unknown, add **metric/log** in the slice that implements that step.

---

## Test strategy (test-strategist lens)

### Layer 0 — Contract (both repos)

- **PFOS:** Vitest for `isAgentEventPayload`, `SurfaceKind`, API route handlers (existing patterns).
- **agents:** pytest for gateway slack ledger, `__main__` in-process, any new `pfos_emit` client (mock HTTPS).

### Layer 1 — Integration (local)

- **PF Runtime:** `bash scripts/pf-qa.sh` after every meaningful change.
- **PFOS:** `npm run verify`.

### Layer 2 — Cross-repo smoke (manual or scripted)

- Curl ingest to **staging** PFOS with test bearer → expect 200 → row visible in Supabase SQL or count endpoint.
- Slack test workspace message → runtime log line → event row (non-prod bot).

### Layer 3 — Regression / policy

- **`fleet-coverage-gate.sh`** (PFOS): journalctl patterns match new runtime unit names + log vocabulary once ADR defines them.
- **Threat model:** [`pf-runtime/docs/THREAT_MODEL.md`](file:///Users/alexhale/Projects/agents/pf-runtime/docs/THREAT_MODEL.md) — when new ingest/vault paths ship, add or extend `tests/threat_scenarios/` (currently sparse per doc).

### Coverage / quality floors

- Keep **`cov-fail-under`** in `pf-runtime/pyproject.toml` at current bar (70) unless total drops; raise only with margin.
- **PFOS:** no global coverage mandate in `verify`; add **one Playwright spec** for `/agents` playground when UI lands.

---

## SRE / operability (gated keywords: deploy, vercel, prod)

| Concern                                       | Action                                                                                                                                                                     |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Vercel** env vars for ingest URLs / secrets | Document in `docs/pfos-mnesk-ops.md`; separate staging vs prod                                                                                                             |
| **VPS** PF Runtime                            | systemd/launchd unit named consistently `pf-runtime-*` for grep in [`fleet-coverage-gate.sh`](file:///Users/alexhale/Projects/prettyfly-os/scripts/fleet-coverage-gate.sh) |
| **Rollback**                                  | Re-enable Hermes plist + disable PF Runtime job; ADR states window                                                                                                         |
| **Cron**                                      | PFOS cron jobs unchanged unless playground triggers new routes — if so, add `vercel.json` entry + `CRON_SECRET` pattern                                                    |

---

## Data integrity (gated: supabase, migration)

- **Migration discipline:** `SurfaceKind` TS + Postgres CHECK must update in **one PR** or two atomic PRs with deploy order documented (migration before app deploy).
- **RLS:** New playground queries must use existing `company_id` scoping — **no** new service-role reads from client components.

---

## Concurrency / idempotency

- **Slack outbound:** SQLite ledger + in-memory dedup ([`slack.py`](file:///Users/alexhale/Projects/agents/pf-runtime/pf_runtime/channels/slack.py)) — extend tests if ingest client adds retries.
- **agent_events:** ADR should state whether duplicate `(type, trace_id)` is acceptable or needs unique partial index later.

---

## Supply chain

- **agents:** `uv.lock` committed; `pip-audit` in pf-qa.
- **PFOS:** `npm audit` on cadence; no new deps for playground v0 unless required for UI.

---

## Implementation phases (TASK_LIST)

### Phase P0 — ADRs + exit criteria (paper)

1. Draft **ADR-A–D** (product/runtime, Slack, data plane, GitHub) in memory-vault + `agents/_meta/decisions/` copies.
2. Add **exit criteria** checkboxes (Iris E2E, pf-qa, verify, prod smoke).

### Phase P1 — PFOS schema + types

1. Supabase migration: allow `pf_runtime` on `agent_events.surface` (or agreed enum).
2. Update [`lib/agentEvents.ts`](file:///Users/alexhale/Projects/prettyfly-os/lib/agentEvents.ts) `SURFACE_KINDS` + guards.
3. Vitest for new surface.

### Phase P2 — PF Runtime emit client

1. Small `pfos_emit` module (env-gated): POST body matches `AgentEventWritePayload`.
2. pytest with `httpx`/`urllib` mocked.
3. Gateway hook: inbound/outbound milestones emit events (configurable noise level).

### Phase P3 — Playground UI (PFOS)

1. Replace [`app/agents/page.tsx`](file:///Users/alexhale/Projects/prettyfly-os/app/agents/page.tsx) shell: Iris status, last event, fleet link.
2. Optional: server component query `agent_events` (RLS-safe).

### Phase P4 — Vault read spike (Iris B4)

1. Implement **one** read path per ADR-C decision (post-spike).
2. Record latency + auth model; lock ADR-C.

### Phase P5 — GitHub read → write (gated)

1. Read issues/PRs per ADR-D.
2. Write behind `PFRT_GITHUB_WRITE=1` + event audit.

### Phase P6 — Operator hardening

1. Extend [`scripts/pf-cutover-preflight.sh`](file:///Users/alexhale/Projects/agents/scripts/pf-cutover-preflight.sh) or sibling: verify env keys visible to **launchd** context (documented probe).
2. Update [`CUTOVER_C_PLAYBOOK.md`](file:///Users/alexhale/Projects/agents/.planning/phase-4-7-prettyfly-runtime/CUTOVER_C_PLAYBOOK.md) cross-link.

---

## Risk assessment

| Risk                                        | Severity     | Mitigation                                  |
| ------------------------------------------- | ------------ | ------------------------------------------- |
| Missing API keys under launchd (STATUS)     | **critical** | Preflight + copy pattern from global `.env` |
| Enum drift TS vs DB                         | **high**     | Single PR + integration test                |
| Ingest token leakage in logs                | **high**     | Redact in structured logging                |
| Playground queries without RLS              | **critical** | Code review checklist                       |
| Scope creep (multi-agent before Iris green) | **medium**   | ADR-A Phase A rule                          |

---

## Verification passes (--deep = 3)

### Pass 1 — Static + unit (automated)

- [ ] `cd ~/Projects/agents && bash scripts/pf-qa.sh`
- [ ] `cd ~/Projects/prettyfly-os && npm run verify`
- [ ] Migrations apply clean on fresh Supabase branch (if available)

### Pass 2 — Integration (staging)

- [ ] Ingest smoke: bearer POST → 200 → row query
- [ ] Slack non-prod: one message → event row
- [ ] Playground renders last event for pilot tenant

### Pass 3 — Operability + rollback

- [ ] `fleet-coverage-gate.sh` dry-run documents expected counts (not necessarily PASS threshold)
- [ ] Kill PF Runtime job → PFOS shows stale / degraded state clearly
- [ ] Rollback: Hermes job restored per playbook timing

---

## `/build-stack` chain (post-plan confirmation)

When implementing slices after you **confirm this plan**:

```text
/build-stack ~/Projects/agents/.planning/pf-runtime-pfos-planning-stack-deep-2026-05-07.md --tdd --review
```

Notes:

- **`build-stack` has no `--deep` flag** in the skill; interpret **deep** as: **multi-batch TDD** (per phase), **three verification passes** above, then **`--review`** (or Codex `$staged-review`).
- Add **`--audit`** only for PFOS web/Lighthouse work; **skip for Python-only** slices unless you add a web surface in the same batch.

---

## Explicit non-goals (this plan cycle)

- Multi-tenant white-label (Stage 7) before Iris GA.
- Full Hermes retirement outside PrettyFly.
- PFOS subprocess supervision of PF Runtime.

---

## Related artifacts

- Integration product plan: `~/.cursor/plans/pf_runtime_×_prettyfly_os_—_integration_plan_(contract-first)_b7cd2da7.plan.md`
- Phase 4.7: [`agents/.planning/phase-4-7-prettyfly-runtime/`](file:///Users/alexhale/Projects/agents/.planning/phase-4-7-prettyfly-runtime/)
- PFOS roadmap: [`prettyfly-os/.planning/ROADMAP.md`](file:///Users/alexhale/Projects/prettyfly-os/.planning/ROADMAP.md)

---

## Sign-off block (fill before implementation)

- [ ] ADR-A–D reviewed
- [ ] Iris `agent_slug`, Slack workspace, pilot `company_id` filled
- [ ] Vault read path chosen post–B4 spike
- [ ] Owner for VPS vs Vercel env rotation named

**Planner output:** planning-stack **deep** complete for QA/QC + PF Runtime × PFOS integration. **Await explicit user confirmation** before `/build-stack` execution per planning protocol.
