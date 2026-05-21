# Changelog — technical-operator profile

## 2026-05-21 — runtime smoke against synced Hermes profile

- Runtime sync checked with `scripts/sync-profile.sh status technical-operator`:
  versioned and runtime tracked files match; no profile push needed before the
  first attempt.
- Direct Anthropic route was blocked by exhausted direct Anthropic credentials;
  `technical_review` now routes through funded OpenRouter as
  `openrouter:anthropic/claude-sonnet-4.6`.
- Patched `scripts/fleet-invoke.sh` so explicit provider-prefixed model IDs
  containing `/` become `--provider <provider> -m <model>` instead of falling
  through to the global Hermes provider.
- Provisioned PFOS `agents.slug='technical-operator'` for the PrettyFly tenant
  so `agent_slug=technical-operator` writeback resolves instead of returning
  `agent_slug_not_found`.
- Smoke target:
  `hermes/profiles/technical-operator/skills/technical-review.md`.
- Smoke output:
  `_inbox/technical-operator-reviews/2026-05-21-review-technical-operator-technical-review.md`.
- PFOS event:
  `ec805034-209a-4515-9010-a525ab1f57ca`
  (`type=technical_operator.review.proposed`, `agent_slug=technical-operator`,
  `skill_slug=technical-review`, `surface=cli`, `cwd_project=agents`).
- Verdict: `SHIP-RISK-MEDIUM` smoke evidence, TYPE-2. Follow-up findings are
  bounded to emitter failure semantics and token-env path documentation; no
  authority expansion, promotion, channels, sends, deploys, or merges.

## 2026-05-20 — rung 1 scaffold

- Created via direct write (no `scripts/bootstrap-profile.sh` run); 11-file
  Atlas contract.
- Locked at rung 1 (read-only on review target, propose-only writes to
  `~/Projects/agents/_inbox/technical-operator-reviews/`).
- Channels: none.
- Authority: `technical_review.propose` only. No deploy, merge, send, or
  production-mutation tools.
- Inherited 20 engineering Agency shared skills previously parked under
  `PARKED_CANDIDATES["technical-operator"]` in
  `scripts/build-agency-shared-skills.py`. Build script updated to move them
  from parked to active under this profile.
- One profile-local skill: `technical-review`.
- Event type: `technical_operator.review.proposed`. Underscore form chosen for
  consistency with existing fleet events (`marin.*`, `stet.*`, `atlas.*`).
- Scope ADR: `_meta/decisions/2026-05-20-technical-operator-profile-scope.md`.
- Codex-boundary ADR: `_meta/decisions/2026-05-20-reserve-codex-for-tool-use-technical-operator-profile.md`.
- Smoke target: existing skill files in `hermes/profiles/marin/skills/` or
  `hermes/profiles/stet/skills/`.
- Promotion to rung 2+ requires a separate ADR.
