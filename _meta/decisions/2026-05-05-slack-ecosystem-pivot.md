# ADR-004 — Slack-native ecosystem replaces Telegram-first plan

**Date:** 2026-05-05
**Status:** Accepted (supersedes Phase 1.5 Telegram pairing target; rewrites decision #11; pulls Phase 4 MC retirement forward)
**Operator authorization:** "We will make this new path the sole forward option by retiring all other Slack references, connections, and related items… full permission" (Alex, 2026-05-05 PM)

## Context

The architecture's original Phase 1.5 transition required pairing a new Telegram bot for the `personal` profile (operator-only @BotFather step). That blocked all Hermes profile activation.

Alex uses Slack significantly more than Telegram, has the prettyfly.ai workspace already provisioned, has Mission Control's Slack bot running on VPS:3457 (now stagnant by his report), and has authorized full replacement.

Three subagents researched the pivot in parallel:

- **`/tmp/agentic-os-research/20-mc-slack-audit.md`** — asset inventory of the existing MC bot. 8 channels, 7 agents, scopes catalogued, env vars listed, decommission risks enumerated.
- **`/tmp/agentic-os-research/21-slack-multi-agent-patterns.md`** — 2026 patterns research. Locked recommendation: **Architecture B (bot-per-agent-tier)** — 13 Slack apps, one per profile, OAuth-scope-enforced read-only on money pipelines.
- **`/tmp/agentic-os-research/22-hermes-slack-plugin-spec.md`** — confirmed Hermes 0.12.0 ships **first-party native Slack gateway** (`hermes slack manifest`, `hermes-slack` toolset preset, parity with Telegram). No plugin to build.

## Decision

**Replace the 8-channel MC Slack ecosystem with a 13-bot Hermes-native Slack ecosystem in the same prettyfly.ai workspace.** Architecture B (one Slack app per Hermes profile) using Hermes' built-in Slack gateway. No custom plugin code. No phased coexistence with the MC bot — full retirement at cutover.

### Concrete shape

| Aspect                           | Value                                                                                                                                                   |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Workspace                        | prettyfly.ai (existing)                                                                                                                                 |
| Number of Slack apps             | 13 (one per chartered profile)                                                                                                                          |
| Manifest generator               | `hermes slack manifest --name "<AgentName>"`                                                                                                            |
| Toolset preset                   | `hermes-slack` (= terminal, file, web, vision, image, tts, browser, skills, todo, cronjob, messaging)                                                   |
| Connection mode                  | Socket Mode (no public ingress)                                                                                                                         |
| Per-profile config key           | `platform_toolsets: { slack: [hermes-slack] }` + tokens in profile `.env`                                                                               |
| Money-pipeline scope restriction | Vanclief, sportsbook get manifests with `chat:write`/`im:write`/`reactions:write`/`files:write` removed — read-only enforced by Slack OAuth, not config |
| Voice path                       | `file_shared` audio events → Whisper transcribe → text reply (ElevenLabs TTS optional)                                                                  |
| Honcho session key               | `agent:<profile>:slack:<channel>:<thread_ts>` per profile peer                                                                                          |
| Deploy target                    | VPS 167.71.113.40, gateway on existing Hermes runtime, port 3467 reserved if HTTP health needed (not required for Socket Mode)                          |

### What gets retired

- `~/Projects/mission-control/slack-bot/` — archived in `_archive/2026-05-mc-slack-bot/`
- 8 `#mc-*` channels — deleted or repurposed at cutover (greenfield naming uses Hermes profile slugs: `#atlas-ceo`, `#viper-outreach`, `#quill-content`, etc.)
- MC's existing Slack app — Event Subscriptions disabled in Slack API console **before** new apps activate to prevent duplicate dispatch
- `mc-slack-bot.service` systemd unit — stop + disable at cutover
- `slack_channels` Postgres table — truncate at cutover
- Legacy `SLACK_WEBHOOK_URL` / `SLACK_BOT_NOTIFY_URL` env vars — removed

### What survives (asset reuse)

- Slack workspace identity (prettyfly.ai)
- Workspace IDs and the practitioner pattern (Block Kit approval cards, mdToMrkdwn formatting, double-click protection, HMAC verification — all native to Hermes' Slack gateway)
- Per-agent voice/persona rules from MC's `/opt/mission-control/workspace-{agent}/SOUL.md` (pulled to local before decommission, ported into Hermes profile SOUL.md files)

## Consequences

### Decisions rewritten

| Original                                                                  | Rewritten                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Decision #11 (channel discipline: Telegram daily, Slack weekly narrative) | **Slack is now both the daily and weekly channel** for all 13 profiles. Telegram is retired from the substrate. Voice modality moves to a future phase using Slack `file_shared` audio events (Whisper) + optional ElevenLabs TTS replies — no more dependence on Telegram voice. |
| Master plan Phase 1.5 (Telegram bot pairing for personal)                 | **Phase 1.5 = Slack ecosystem provisioning.** Operator browser-required step is "create 13 Slack apps via the Slack admin UI or `apps.manifest.create` REST endpoint with the `hermes slack manifest` JSON," not BotFather.                                                       |
| ADR-001 Phase 4 MC retirement (calendar-bound to ~2026-07-24)             | **Pulled forward to Phase 1.5–2 window.** MC retirement happens at Slack cutover. Phase 4's other elements (Honcho on VPS, LAIK fusion) keep their original timing.                                                                                                               |
| Decision #14 LAIK fusion (Phase 4.5)                                      | **Unchanged.** LAIK timing remains Phase 4.5; the MC retirement pulled forward affects only the MC half of original Phase 4.                                                                                                                                                      |
| `personal/CLAUDE.md` acceptance gate                                      | **Rewritten:** "7 consecutive days of Slack DM/channel replies that reference yesterday's conversation correctly via Hermes session DB recall." Voice constraint dropped from this gate; voice becomes a separate future phase.                                                   |

### Decisions reaffirmed (unchanged)

- Decision #1 (SQLite WAL + Honcho bus): Honcho is the substrate. Slack is a gateway _to_ the substrate, not a replacement.
- Decision #2 (single Honcho workspace `prettyfly-os`, peer per profile): unchanged.
- Decision #5 (Wilson-CI ≥0.80 lower-bound eval gate): unchanged. Email-triage SKU still gates Phase 1 advance.
- Decision #12 (Honcho AGPL server-side only): unchanged.
- Decision #13 (money-flowing pipelines read-only): now enforced _more strongly_ via Slack OAuth scope omission, not just code-level checks.
- Decision #16 (`agora` substrate brand, moltbook.com integration rejected): unchanged.

## Cutover sequence (Karpathy ladder, no dual-run)

| Step | Action                                                                                                                                                                                                                                               | Gate measurement                                                                                                                                    |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | Pull MC SOUL.md voice rules off VPS into local profile dirs                                                                                                                                                                                          | All 7 voice files present at `~/Projects/agents/hermes/profiles/{atlas-ceo,viper-outreach,quill-content,forge-audit,lawdbot,ops}/MC-VOICE-NOTES.md` |
| 2    | `ssh root@167.71.113.40 'systemctl stop mc-slack-bot && systemctl disable mc-slack-bot'` + disable old Slack app's Event Subscriptions in API console + truncate `slack_channels` table                                                              | `systemctl status mc-slack-bot` returns inactive; old app's webhook URLs removed from Slack admin                                                   |
| 3    | Generate 13 Slack manifests: `hermes slack manifest --name "<AgentName>" --description "<role>" > /tmp/<slug>.json` for each profile. Money-pipeline manifests: also pass `--slashes-only` and merge into a custom manifest that omits write scopes. | 13 manifest files produced; `vanclief.json` and `sportsbook.json` lack `chat:write`                                                                 |
| 4    | Operator step: create 13 Slack apps in `prettyfly.ai` workspace via `apps.manifest.create` REST or admin UI. Capture `xoxb-*` + `xapp-*` tokens per app.                                                                                             | 13 apps installed in workspace; tokens stored in macOS Keychain `slack-bot-<profile>` and `slack-app-<profile>` slots                               |
| 5    | Per-profile `.env` populated with `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`. `~/.hermes/profiles/<name>/config.yaml` enables `platform_toolsets: { slack: [hermes-slack] }`.                                                                              | `hermes profile show <name>` reports Slack gateway active                                                                                           |
| 6    | First profile (atlas-ceo, lowest-risk) — start its gateway, post a daily-brief test message to `#atlas-ceo`, validate one approval-card round-trip                                                                                                   | atlas-ceo posts cleanly for 3 days; one full approval flow round-trips through Hermes interactivity handler                                         |
| 7    | Fan out remaining 12 profiles                                                                                                                                                                                                                        | Each profile passes its own SKU gate (when applicable) or 24h zero-error soak                                                                       |
| 8    | Phase 1 acceptance gate (rewritten): personal profile completes 7 consecutive days of correct yesterday-context recall in Slack                                                                                                                      | TSV log of Hermes session-DB recalls per day; eyeball + Honcho semantic match check                                                                 |

## Stop conditions

- **Duplicate dispatch detected** (old MC app still subscribed): halt step 6, return to step 2, fully revoke old subscriptions in Slack API console.
- **Money-pipeline manifest accidentally includes `chat:write`**: hard stop; vanclief/sportsbook must be read-only by OAuth, not by convention.
- **Honcho session-key collision** (two profiles writing to the same Honcho peer): halt activation, fix `slack.json` or per-profile config so each profile is a distinct Honcho peer.

## References

- `/tmp/agentic-os-research/20-mc-slack-audit.md`
- `/tmp/agentic-os-research/21-slack-multi-agent-patterns.md`
- `/tmp/agentic-os-research/22-hermes-slack-plugin-spec.md`
- [Hermes Slack Gateway Docs](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/slack)
- [OpenClaw Multi-Agent Slack pattern](https://gist.github.com/rafaelquintanilha/9ca5ae6173cd0682026754cfefe26d3f)
- ADR-001 (Hermes adoption), ADR-002 (VanClief world-model audit), ADR-003 (Substrate architecture)
