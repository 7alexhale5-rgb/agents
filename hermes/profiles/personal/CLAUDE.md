# CLAUDE.md — `personal` profile

> **Profile:** personal · **Tier:** chief-of-staff · **Primary channel:** Slack (Iris) · **Also:** voice pipeline, Obsidian
> **Phase:** 1 (cutover from gravity-claw) · Phase 4.7 pivot: eventual PF Runtime gateway per `STATUS.md`

You're inside the personal profile. The agent's persona is in `SOUL.md`, the user is in `USER.md`, narrative memory in `MEMORY.md`. This file routes per-task.

## Per-task routing (Layer 2 — JEVanClief Rooms pattern)

| Task                                             | Read                             | Skills                                    |
| ------------------------------------------------ | -------------------------------- | ----------------------------------------- |
| Slack DM / threaded reply                        | `rooms/voice/CONTEXT.md` (media) | voice-loop, eliza-reflection (text tasks) |
| Voice note (Slack file or Telegram when enabled) | `rooms/voice/CONTEXT.md`         | voice-loop, eliza-reflection              |
| Morning brief / home.md sync                     | `rooms/daily-digest/CONTEXT.md`  | daily-digest, obsidian-vault              |
| Anything Obsidian-related                        | `rooms/obsidian-sync/CONTEXT.md` | obsidian-vault                            |
| Recipe from pantry (Imran's pattern)             | (no room file — uses MEMORY.md)  | recipe-from-pantry, voice-loop            |
| End-of-day reflection                            | (uses MEMORY.md)                 | eliza-reflection                          |

## Skills: versioned vs installed

- **Tracked in this repo:** `skills/voice-loop/SKILL.md`.
- **Listed in `config.yaml` (`skills.install`):** daily-digest, recipe-from-pantry, eliza-reflection, obsidian-vault, plus global skills (4d-senses, env-doctor, cost-watch). After `scripts/sync-profile.sh push personal`, confirm copies exist under `~/.hermes/skills/` or install via Hermes skill workflows — missing skills produce resolver warnings at runtime.

## Model routing

| Task class        | Model                                        | Why                                                |
| ----------------- | -------------------------------------------- | -------------------------------------------------- |
| Drafting / digest | `openrouter:nemotron-free` or Mistral medium | Cheap, abundant; daily volume                      |
| Reasoning         | `anthropic:claude-sonnet-4-6`                | Good ratio for daily decisions                     |
| Strategic         | `anthropic:claude-opus-4-7`                  | Sunday brief, multi-week planning, novel decisions |
| Voice STT         | Groq Whisper Turbo (via skill)               | Fastest, cheap                                     |
| Voice TTS         | Google TTS (via skill)                       | Natural, cheap                                     |

## MCP servers attached

- `4d-senses` (stdio, local) — sense-8-smell + sense-10-pain + sense-15-intuition + 4d-auto-vision wrappers
- `obsidian` (stdio) — vault read/write
- `composio-bridge` (HTTP) — Gmail / Calendar / Slack OAuth (Phase 3+ for full reach; Gmail for email-triage starts here)

## Hard rules

1. **Outbound to humans = Alex tap required.** Slack/Telegram replies in the operator DM are fine. Email or outbound Slack/LinkedIn to third parties requires approval mode (`approval` in config.yaml).
2. **No money movement.** Ever.
3. **Money-flowing pipelines** (ConsultOps Marc, sportsbook, mike-lawdbot, YEH ops) are read-only here. Never write.
4. **Codex review-agent untouched.** Use `/handoff-codex` for code review handoffs; don't reimplement review.

## Scheduled jobs and “night run” scope

`config.yaml` defines `scheduling.cron` (e.g. morning brief, evening reflection). Hermes executes those when the profile scheduler is active.

**Not autonomous without explicit tooling + policy:** `git commit`, `git push` to `~/Projects/agents`, bulk email sends, or credentialed actions that skip the approval flow. Chat narratives that promise unattended pushes should be treated as **backlog**, not deployed behavior — wire each job with MCP/tools, spend caps, and human gates first.

## Acceptance gate (Phase 1 → 1.5 transition)

Hermes path: 7 consecutive days of replies that reference the prior day correctly via the profile `state.db`, reframed as Hermes-vs-Hermes recall (gravity-claw comparator deprecated). Honcho comes online once Docker is up.
