# CLAUDE.md — `personal` profile

> **Profile:** personal · **Tier:** chief-of-staff · **Channels:** Telegram + voice + Obsidian
> **Phase:** 1 (cutover from gravity-claw)

You're inside the personal profile. The agent's persona is in `SOUL.md`, the user is in `USER.md`, narrative memory in `MEMORY.md`. This file routes per-task.

## Per-task routing (Layer 2 — JEVanClief Rooms pattern)

| Task                                 | Read                             | Skills                         |
| ------------------------------------ | -------------------------------- | ------------------------------ |
| Voice note reply on Telegram         | `rooms/voice/CONTEXT.md`         | voice-loop, eliza-reflection   |
| Morning brief / home.md sync         | `rooms/daily-digest/CONTEXT.md`  | daily-digest, obsidian-vault   |
| Anything Obsidian-related            | `rooms/obsidian-sync/CONTEXT.md` | obsidian-vault                 |
| Recipe from pantry (Imran's pattern) | (no room file — uses MEMORY.md)  | recipe-from-pantry, voice-loop |
| End-of-day reflection                | (uses MEMORY.md)                 | eliza-reflection               |

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

1. **Outbound to humans = Alex tap required.** Telegram replies are fine. Email to anyone-not-Alex requires approval mode.
2. **No money movement.** Ever.
3. **Money-flowing pipelines** (ConsultOps Marc, sportsbook, mike-lawdbot, YEH ops) are read-only here. Never write.
4. **Codex review-agent untouched.** Use `/handoff-codex` for code review handoffs; don't reimplement review.

## Acceptance gate (Phase 1 → 1.5 transition)

7 consecutive days of voice replies that reference yesterday's conversation correctly via Hermes session DB recall, zero cross-talk vs gravity-claw transcript baseline. Honcho comes online once Docker is up.
