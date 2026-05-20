---
name: profile-from-template
description: Use when scaffolding a new Hermes profile from the Atlas-shaped template — koho-ops, yeh-ops, a new domain operator, anything that needs the standard config.yaml + CLAUDE.md + persona files + manifest + a2a-card. Triggers on phrases like "new profile", "scaffold a profile for X", "set up <name> as a Hermes agent", "/new-employee". Takes a short interview, generates a rung-1 read-only skeleton, syncs to runtime, and runs lint. Cuts the manual Atlas-template walk from ~2 hours to ~5 minutes.
---

# Profile-from-Template

A scaffold skill — interview the user, build a minimal valid Hermes profile, lint-pass it, push to runtime. Always rung 1 (read-only) on first scaffold; the user customizes after to add proposed-write tools, event contracts, and skills.

## When to use

Invoke when the user says any of:

- "new profile", "scaffold a profile", "set up <name> as a Hermes agent"
- "/new-employee"
- "build me a profile for <domain>"
- "I need a koho-ops / yeh-ops / <other> profile"
- references the `profile-from-template` skill by name

Don't invoke for:

- Editing an existing profile (just edit the files directly)
- Adding a skill to an existing profile (write the skill markdown directly)
- Renaming or archiving a profile (manual git work)

## The interview

Ask the user these in order. Build the answers into a JSON config (shape below). If the user gives terse answers, use the defaults shown.

1. **Profile name** (kebab-case, must match `^[a-z][a-z0-9_-]{1,30}$`). No default.
2. **One-line description** for the manifest tagline. No default.
3. **Domain / cwd_project**. The marketing vault key, repo slug, or PFOS silo this profile reports under. Examples: `marketing`, `agents`, `koho`, `yeh`. No default.
4. **Channels.** One of `none` (writes to inbox only), `slack_dm`, `telegram`. Default `none`.
5. **Daily cap.** Integer per `fleet/limits.json`. Default `1` (rung-1 is read-only so this is the cap for whenever they add a propose tool later).
6. **Default model.** Default `openrouter:nvidia/nemotron-3-nano-30b-a3b:free`.
7. **Escalation model.** Default `anthropic:claude-sonnet-4-6`.
8. **Source read tool name** in `<domain>.<verb>` form. Default `<domain>_vault.read`. This is the only tool the scaffolded profile ships with — the agent later adds propose tools manually.

If the user wants a propose-write tool baked in from day one, decline politely and explain: scaffolds are rung 1 by design (read-only). Adding propose tools requires an event contract, a rate-cap allocation, and PFOS event-type registration — those are intentional steps, not auto-generated. Point them at Marin's `weekly_decision.propose` as the reference pattern.

## How to scaffold

After the interview, build the JSON config and run the scaffolder:

```bash
cat > /tmp/profile-config.json <<'JSON'
{
  "profile_name": "<from-interview>",
  "description": "<from-interview>",
  "domain": "<from-interview>",
  "channels": "<none|slack_dm|telegram>",
  "daily_cap": <int>,
  "model_default": "<default-route>",
  "model_escalate": "<escalation-route>",
  "source_tool_name": "<domain.verb form>"
}
JSON
python3 ~/Projects/agents/hermes/skills/profile-from-template/scaffold.py --config /tmp/profile-config.json
```

The scaffolder will:

1. Validate the config and refuse if the profile already exists (no silent overwrite).
2. Copy every file from `_template/` to `hermes/profiles/<name>/` with placeholders substituted.
3. Create empty `skills/`, `eval/`, `memory/` directories.
4. Create the `AGENTS.md` → `CLAUDE.md` symlink.
5. Append the rate-cap entry to `fleet/limits.json` (only if missing — never overwrites an existing cap).
6. Run `scripts/lint-profile.sh <name>` and fail loud if any warning fires.

If lint passes the scaffolder prints the next manual steps — push to runtime via `scripts/sync-profile.sh push <name>`, then add propose-write tools and skills as the profile graduates from rung 1.

## Placeholder convention

Templates use `__KEY__` for substitution (not `{{KEY}}` — curly braces clash with JSON literals). The full key list is in `scaffold.py:REQUIRED_KEYS`. A scaffold with all keys filled produces a profile that lints clean on first run.

## After scaffold

Read the new profile's CLAUDE.md and tell the user the three things they still need to do before the profile is useful:

1. Fill in `SOUL.md` (persona), `DOCTRINE.md` (operating principles), `USER.md` (what the agent knows about Alex), `MEMORY.md` (environment facts).
2. Add at least one proposed-write tool with a full `event:` contract block (use Marin's `weekly_decision.propose` as the template — copy the shape, change the type/skill*slug/data*\* keys).
3. Cross-link the event type into CLAUDE.md (the lint cross-check requires it).

Stop there. Don't auto-fill the persona files — those are domain-specific and need the user's voice and context, not a generic template.

## Karpathy gate

This skill clears its gate when:

- A throwaway profile scaffolds end-to-end with zero manual touches.
- `scripts/lint-profile.sh <name>` returns `PASS`.
- The agent picking up the scaffolded profile knows what to fill in next.

Test fixture lives at `evals/fixture-throwaway.json`. Run it to verify the skill still works after any template change.
