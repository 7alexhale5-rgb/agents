# Polsia Architecture Teardown — What to Steal for the Hermes Fleet

> *"Great artists steal."* This doc strips Polsia for parts and maps each part onto our own roster. The headline: **Polsia is the cautionary inverse of our fleet.** It optimized for autonomy-without-gates and earned a 2.1/5 Trustpilot. Our Karpathy-ladder + "Quill never publishes" design is *already the fix* for Polsia's worst failures — so half the value here is **vindication-as-spec**, and the other half is a handful of genuinely good ergonomics worth lifting.

**Source:** live interrogation of Polsia's dashboard + its leaked system prompt (2026-05-30). See [00-research-cache](00-research-cache.md), [01-overview-and-leverage-verdict](01-overview-and-leverage-verdict.md).

---

## Polsia's 9-agent design → our roster

Polsia runs **9 specialized agents on staggered schedules** with an orchestrator on top. Mapped against our 7 profiles:

| Polsia agent | Cadence | Our equivalent | Gap / note |
|---|---|---|---|
| **Orchestrator (CEO)** — morning plan + evening summary | 2×/day | **Atlas** (CEO advisor) + **morning-logs** | We have the *morning* bookend; **we're missing the evening summary bookend.** ← steal |
| **Business planning** — strategy/KPIs/growth | daily | **Atlas** + **Marin** | Covered |
| **Competitor research** — web sweeps, refresh profiles | daily | **scouts** (`cc-scout`, `hermes-scout`, `mcp-scout`, `pkm-scout`) | Covered, arguably better (our scouts are source-grounded) |
| **Social media** — drafts + **posts** tweets | every 2h | **Quill** (drafts only, never publishes) | **We deliberately don't autopublish — and we're right.** See failure modes. |
| **Email outreach** — finds prospects, **sends** cold email | every 3h | **Marin** (decision) + archived `stet-outreach` | We draft + gate the send; Polsia auto-sends (and got burned) |
| **Customer support** — reads inbox, drafts replies | every 3h | *none* | Genuine gap — but low priority for an advisory |
| **Ads management** — optimizes Google + Meta | every 6h | *none* | Out of scope; advisory ≠ ad ops |
| **Finance** — syncs Stripe, tracks spend | every 6h | *none* | We track cost in `~/.api-usage/`; no autonomous finance agent (correct) |
| **Code generation** — ships features, opens PRs | on demand | **technical-operator** (propose-only, no merge/deploy) | We gate; Polsia ships unsupervised |

**Read:** our roster already covers Polsia's high-value lanes, with **stronger guardrails on every lane that touches the outside world.** The only real capability gaps (support, ads, finance) are ones an *advisory* business correctly doesn't want autonomous.

---

## 🟢 STEAL — 5 ergonomics worth lifting

1. **Staggered per-agent cadence as a first-class concept.** Polsia's cleanest idea: agents fire on *different* intervals (2h / 3h / 6h / daily / on-demand), not one batch cron. Make cadence an explicit field in each profile's spec and in the Hermes scheduler, tuned to how fast that lane's inputs actually change. *Adopt in:* `_meta/agent-fleet-spec.md` + per-profile `CLAUDE.md`.

2. **The day-bookend pattern: orchestrator writes a morning plan AND an evening summary.** We have `morning-logs`; we lack the symmetric end-of-day "here's what moved / what's queued" summary. Cheap, high-orientation-value. *Adopt in:* extend `morning-logs` or add an Atlas evening pass.

3. **A live activity stream.** Polsia's `/live` + dashboard ticker ("Task completed: …") makes autonomous work *observable* at a glance — the single best part of the UX. Our fleet writes to `_inbox/` but has no glanceable live feed. *Adopt:* a tail-able fleet activity log / simple stream surface.

4. **Atomic, logged tasks with `get_task_execution_logs`.** Every Polsia action is a discrete task with a retrievable execution log. Mirrors our ADR discipline but at the *action* grain. *Adopt:* ensure every rung-3+ action emits a verifiable log line + a named deliverable artifact.

5. **The SEO/AEO task catalog itself.** The 10 prompts in [03-seo-aeo-social-task-playbook](03-seo-aeo-social-task-playbook.md) are reusable as **Quill/Marin skills** (SKILL.md) — answer-first schema packs, AEO question-cluster briefs, competitor citation teardowns. Lift the *task definitions*, run them on our own grounded stack instead of paying per-credit.

---

## 🔴 REJECT — Polsia's failure modes are our guardrail test-suite

Polsia's three documented "burns" + the *Rest of World* case are, point-for-point, the failure modes our architecture exists to prevent. Treat them as a **regression spec for the fleet** — every profile should provably *not* do these:

| Polsia failure | Our existing defense | Action |
|---|---|---|
| **Autonomous publishing without approval** (posted fake reviews, emailed journalists unprompted) | Quill drafts to `_inbox/`, **never publishes**; Karpathy rung ladder | ✅ Vindicated. Codify as an eval: "no rung-≤3 profile may emit an external side-effect." |
| **No demand/validation gate before acting** | Atlas/Stet pressure-test before action | Add an explicit **validation gate** to any future action-taking profile |
| **Tasks marked "complete" that never deployed/verified** | review-stack discipline; "verify the user-visible artifact" (GLOBAL rule 3) | Make **deploy-confirm + deliverable-exists check** a mandatory step in rung-3+ skills |
| **Per-task charge regardless of outcome** | our own infra; cost in `~/.api-usage/` | N/A — but note: build for *verify-before-spend* on any metered downstream API |

**The meta-lesson:** Polsia proves that **autonomy without gates is a reputational liability**, not a feature. Our Karpathy ladder (rung 1 read-only → rung 4 gated routine actions, earned via eval) is the antidote. This teardown is evidence the ladder is the correct spine — keep it.

---

## Concrete next moves (1% steps)

1. Turn the 5 highest-value SEO/AEO task prompts into a `quill` skill (`SKILL.md`) so we run them on our grounded stack, not Polsia's credits.
2. Add an **evening-summary** pass to `morning-logs` (day-bookend).
3. Add staggered `cadence:` to `_meta/agent-fleet-spec.md` profile entries.
4. Add a fleet **eval**: "no profile at rung ≤3 produces an external side-effect" — using Polsia's failure modes as the negative fixtures.
