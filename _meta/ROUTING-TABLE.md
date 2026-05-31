# Routing Table — Layer-1

JEVanClief's "the simple table that tells the AI for this task, read these files, skip those files, you might need these skills" pattern, applied at the monorepo root.

When you open this repo, this is the first decision: which profile owns the task.

| If the task is…                                  | Profile          | Skills typically used                                    |
| ------------------------------------------------ | ---------------- | -------------------------------------------------------- |
| "Read me a voice note reply in Telegram"         | `personal`       | voice-loop, recipe-from-pantry, eliza-reflection         |
| "Daily morning brief"                            | `personal`       | daily-digest, obsidian-vault                             |
| "Send me a recipe based on my pantry"            | `personal`       | recipe-from-pantry                                       |
| "Triage my Gmail this morning"                   | `personal`       | email-triage (the marketplace starter SKU)               |
| "Review this PR"                                 | `lawdbot`        | antfarm/code-review, antfarm/pr-description-writer       |
| "Plan-implement-test on this branch"             | `lawdbot`        | antfarm/{plan,implement,verify,test,pr,review}           |
| "Refactor across this whole repo"                | `codex`          | code-review, security-review                             |
| "Read SMS to grab a 2FA code"                    | `mobile`         | termux-api-bridge                                        |
| "ConsultOps lead came in via Excel"              | `consultops`     | route-lead, dedupe-against-hubspot, send-routing-email   |
| "Edge alert on a sportsbook line"                | `sportsbook`     | edge-monitor, ev-threshold-check                         |
| "YEH PR needs CI inbox triage"                   | `yeh-ops`        | ci-inbox-triage, soc2-evidence                           |
| "Sunday strategy roll-up"                        | `atlas-ceo`      | weekly-okr-roll-up, kpi-snapshot                         |
| "Find a customer's friction and propose a fix"   | `consultops`     | unreasonable-moment-finder, build-from-friction          |
| "Send 10 outbound emails this week"              | `viper-outreach` | composio-bridge, prospect-research, draft-personalized   |
| "Schedule next week's LinkedIn posts"            | `quill-content`  | content-calendar, draft-post, schedule-post              |
| "Run the SOC2 evidence audit"                    | `forge-audit`    | soc2-evidence, contract-metadata-extract                 |
| "Watch costs, alert on threshold breach"         | `ops`            | cost-watch, daily-burn-rate                              |
| "Audit the agent fleet, draft a Sunday brief"    | `vanclief`       | research-stack, eval-runner, voyager-skill-writer        |
| "Ingest a new framework / decide if we adopt it" | `vanclief`       | ladder-of-ai-failure (4-question filter), research-stack |
| "Run a site-wide SEO audit for prettyflyforai.com" | `sentinel`     | seo-audit, opportunity-score                             |
| "Generate a metadata/schema pack for a page set" | `sentinel`       | metadata-pack, schema-pack                               |
| "Write an AEO content brief for a target topic"  | `sentinel`       | aeo-brief                                                |
| "Tear down a competitor's citation profile"      | `sentinel`       | competitor-teardown, research-stack                      |
| "Score SEO opportunities across the site"        | `sentinel`       | opportunity-score, seo-audit                             |

## Skills shared across profiles

Every profile installs the global pack from `hermes/shared-skills/`:

- 4d-senses · obsidian-vault · gstack-yc · honcho-memory · code-review · git-commit-writer · pr-description-writer · env-doctor · security-review · google-workspace · composio-bridge · eliza-therapist · daily-digest · cost-watch · humanizer · doc-coauthoring · interview-context-builder · voyager-skill-writer · unreasonable-hospitality · unreasonable-moment-finder · build-from-friction · recipe-from-pantry

## When NO profile fits

Two options:

1. The task probably doesn't belong in this monorepo. Ask: "Is this an Alex-as-human task or an agent task?"
2. If it's clearly agentic but no current profile owns it, escalate to VanClief — that profile's job includes recommending new SKUs.

## When MULTIPLE profiles could fit

Default to the lower-leverage profile (the IC-tier skill, not the Department Head). Department Heads run on more expensive models and should only fire on truly head-level work.

## Override

Anything in this table can be overridden by an explicit user instruction. The router exists to prevent the wrong profile firing by accident, not to constrain Alex's authority.
