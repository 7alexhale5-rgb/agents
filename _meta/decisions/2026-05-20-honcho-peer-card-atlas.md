---
date: 2026-05-20
type: decision
status: active
tags: [honcho, memory, atlas-ceo, peer-card, decision]
parent_plan: ~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md
related_adrs:
  - 2026-05-18-hermes-pfos-event-contract.md
supersedes: none
---

# Honcho peer-card enabled for atlas-ceo only

## Decision

Enable Hermes's bundled Honcho memory provider for the `atlas-ceo` profile. Leave `memory.honcho.enabled: false` for `marin`, `quill`, `stet`, and future profiles until the 3-session observation window on Atlas clears.

Configuration:

- `~/.honcho/config.json`: `{apiKey, workspace: "prettyfly-fleet", peerName: "alex", sessions: true, enabled: true}` (chmod 600)
- `~/.hermes/.env`: `HONCHO_API_KEY=<key>` (chmod 600)
- `hermes/profiles/atlas-ceo/config.yaml`: `memory.honcho.enabled: true`
- Free tier on cloud Honcho (1,000 messages/month); Atlas weekly cadence projects 80–200 messages/month — comfortable.

## Why Atlas first

1. **Highest rung** (rung 3) — Atlas already runs on Slack DM, accumulates cross-session context naturally. The peer card has real material to learn from.
2. **Single weekly cadence** — peer-card growth is gradual, observable, easy to audit. Compare to Quill which fires per-draft (high volume, noisy training signal).
3. **Internal-only** — failures (fabrication, drift) are visible to Alex during weekly review, not customer-facing.
4. **Existing acceptance loop** — Atlas's gate already requires Alex-review of every weekly brief. Peer-card drift surfaces in the existing review, no new instrumentation needed.

## Why NOT the others (yet)

- **Marin** (rung 2, weekly): session-bounded shape doesn't benefit from cross-session memory until after Marin's weekly readout cadence stabilizes. Revisit after 4 Atlas weekly briefs ship cleanly with Honcho on.
- **Quill / Stet** (rung 2, drafting bursts): drafts are largely stateless per request. Honcho would add noise without clear signal.
- **Codex** (rebuild pending Phase 5.5): the profile doesn't exist yet.

## Reversibility

TYPE-1. Honcho's peer card accumulates over time. Disabling later does NOT unwrite Atlas's brief references to early peer-card content — the content lives in the prior brief artifacts.

**Mitigations:**

- Separation by profile (only Atlas, not fleet-wide) keeps the blast radius small.
- Alex-review of every Atlas weekly brief catches drift early.
- 3-session observation window before considering rollout to other profiles.
- Cite-the-source rule in the brief lets Alex verify or correct any peer-card-derived claim.

## Rollback procedure

1. Edit `hermes/profiles/atlas-ceo/config.yaml`: `memory.honcho.enabled: true → false`
2. `bash scripts/sync-profile.sh push atlas-ceo`
3. (Optional, irreversible) delete the workspace at honcho.dev to wipe the peer card.

## Acceptance

After 3 atlas weekly briefs with Honcho on, all of these must hold:

1. Peer-card injection events appear in `~/.hermes/profiles/atlas-ceo/logs/*.jsonl` trajectory logs.
2. honcho.dev dashboard shows Alex's peer profile building (messages count, derived facts visible).
3. At least one brief explicitly cites a Honcho-derived preference (e.g., "per your stated preference from 2026-05-12 to keep replies under 3 sentences") — confirming the injection is read and used.
4. `USER.md` stays under ~1,375 chars across all 3 sessions (Honcho is additive, not budget-consuming).
5. Zero peer-card-sourced fabrications — every cited preference traces to a real prior session.

If any of these fail, halt rollout to other profiles and triage.

## Cost watch

- Free tier: 1,000 messages/mo per honcho.dev pricing.
- Atlas projected: 20–50 messages × 4 sessions/mo = 80–200 messages.
- Headroom: ~5× over projection — room for ad-hoc Atlas sessions without hitting the cap.
- Escalation: Honcho Pro is $20/mo for 10k messages if volume crosses 1k/mo. Self-host alternative exists (open-source Honcho server runs locally) but not recommended until volume justifies the maintenance.

## Related

- Parent plan: [`~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md`](../../.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md)
- Hermes Honcho integration: `~/.hermes/hermes-agent/plugins/memory/honcho/session.py`
- Hermes config slot: `~/.hermes/hermes-agent/hermes_cli/config.py:1052` (`DEFAULT_CONFIG["honcho"] = {}`)
- Atlas profile config: `hermes/profiles/atlas-ceo/config.yaml`
- Atlas CLAUDE.md memory section: `hermes/profiles/atlas-ceo/CLAUDE.md` § Memory architecture
