# ADR-002 — VanClief gets explicit world-model audit duty

**Date:** 2026-05-04
**Status:** Accepted
**Phase:** Sets the spec for the VanClief profile bootstrap (Phase 1 → Phase 6)
**Supersedes:** Nothing (extends ADR-001)

## Context

The Company AGI fusion report (`~/Projects/research-vault/research/2026-05-04-company-agi-laik-hermes-fusion.md` §5) identifies a gap in the 13-profile org: somebody has to audit the **world model itself** weekly. As tenants accumulate Honcho peer cards, LAIK indexes, MEMORY.md narratives, and crystallized Voyager skills, drift compounds. Without an explicit audit duty, the world model becomes the bug.

VanClief (the AI-Expert profile) is already the Player-coach in the org chart per ADR-001. Mapping ADR-001's three-role frame onto Dorsey's Sequoia podcast structure (IC / DRI / Player-coach), VanClief is the only profile whose primary output is _meta_ — it audits the fleet, ingests new AI research, and ships the Sunday Weekly Brief.

## Decision

VanClief gets four explicit weekly responsibilities:

1. **World-model audit** — every Sunday, run a cross-profile diff:
   - Does the LAIK index match what tenants are saying their company is?
   - Is Honcho dialectic memory drifting (peer cards contradicting fresh evidence)?
   - Are profiles' MEMORY.md files contradicting each other within a tenant?
   - Are crystallized Voyager skills still earning their keep, or have they staled?
     Output goes to the tenant's `console.prettyflyforai.com/dashboard` and to ops profile's eval log.

2. **Ladder-of-AI-Failure four-question filter** on every new SKU/skill/MCP addition before it goes into Lite/Pro/Scale. The four questions:
   - Which abstraction layer does this operate at?
   - What does it replace or compose with?
   - Migration cost vs win?
   - Will the next foundation-model release make it obsolete?
     CI gate refuses publish if VanClief annotates `ladder_test.publishable: false`.

3. **Sunday Weekly Brief per tenant** — already in scope from ADR-001. Post-fusion the brief explicitly cites world-model facts ("this week your customer-pipeline LAIK index added 47 new prospects; viper-outreach drafted 12 emails; conversion trend vs last week"). Loss-leader value prop renders to dashboard for every tenant including starter tier.

4. **Monthly Research Drop** — public blog (PrettyFly OS Keystatic CMS), one technical-deep-dive per month, anonymized aggregate trends across tenant fleet ("across 47 PrettyFly tenants this month, the most common Voyager-crystallized skill was contract-clause-extraction"). Doubles as marketing surface + SEO.

## Authority and scope

VanClief carries `read_only_by_default: true` in its manifest. It cannot mutate other profiles or push to prod. Its outputs are recommendations + drafts. The `atlas-ceo` profile or Alex personally approves PRs that VanClief drafts.

When VanClief detects a P0 condition (eval pass-rate floor breach for 3 consecutive nights, cross-tenant data leak, propose-not-execute bypass) it:

- Pages Alex via Telegram
- Writes a yellow flag to the affected tenant's dashboard
- Drafts a fix PR (does not merge — Codex parallel-review-agent reviews, Atlas approves)
- Logs to `~/Projects/agents/_meta/eval-suites/audit-log.md`

When VanClief detects a P1 condition (model regression, Honcho lag, single-tenant edge case) it:

- Posts to ops profile's daily briefing
- Drafts a fix recommendation in next Sunday Brief
- No paging unless severity escalates

## What VanClief cannot do

- Cannot modify other profiles' SOUL.md / MEMORY.md / USER.md
- Cannot push to production
- Cannot generate compliance opinions (forge-audit owns SOC2 / GDPR)
- Cannot write production code (codex profile builds; VanClief only drafts PRs as recommendations)
- Cannot chase shiny new frameworks — Ladder-of-AI-Failure is the kill-list

## Consequences

- VanClief becomes the eval/audit substrate for the whole marketplace. If VanClief is degraded, every tenant is at risk; if VanClief is sharp, the whole fleet compounds in quality.
- The Sunday Weekly Brief becomes a customer-facing artifact, not just internal. Quality bar rises accordingly.
- Adding a new SKU has explicit gating — it must pass VanClief's four-question filter before publish.
- The public Research Drop creates a marketing surface that's _content-shaped_, not ad-shaped. Compounds SEO + thought-leadership over time.

## How this maps to Dorsey's three-role frame

| Dorsey                                                | Our profile                                                                   | Durable skill                                                                   |
| ----------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| IC (operator with agent access)                       | lawdbot, sportsbook, yeh-ops, mobile, personal                                | judgment / taste / creativity in the moment                                     |
| DRI (owns customer outcome, assembles team)           | atlas-ceo, ops, viper-outreach, quill-content, forge-audit, codex, consultops | ownership / accountability for outcome                                          |
| **Player-coach (builds others' capability by doing)** | **vanclief**                                                                  | **building human capacity / coaching via Sunday Brief, Research Drop, fix PRs** |

VanClief shows how — by doing the audit and writing it up — rather than telling Atlas / Ops how to be better. That's the Dorsey discipline applied to the meta layer.

## Files this ADR governs

- `~/Projects/agents/hermes/profiles/vanclief/SOUL.md` — encode the four duties
- `~/Projects/agents/hermes/profiles/vanclief/CLAUDE.md` — Layer-1 routing for VanClief tasks
- `~/Projects/agents/_meta/eval-suites/audit-log.md` — append-only audit trail
- `~/Projects/agents/marketplace/manifests/vanclief/manifest.json` — when VanClief becomes a sellable SKU (Scale tier bundles it; Lite/Pro tiers get the Sunday Brief portion only)
