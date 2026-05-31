# Org Chart — 12 + 1

The 13-profile fleet, organized as a real org. Each agent has a single specialized job. Each is sold as a marketplace SKU at three tiers (starter / pro / scale).

## C-suite (always installed, free or bundled)

| Profile     | Role            | Channels                     | Memory                        |
| ----------- | --------------- | ---------------------------- | ----------------------------- |
| `atlas-ceo` | Chief Executive | Slack daily brief + Obsidian | Honcho strategic + MEMORY.md  |
| `ops`       | Chief Operating | Slack briefing + dashboard   | Honcho ops + cost-watch skill |
| `personal`  | Chief of Staff  | Telegram voice + Obsidian    | Honcho personal + MEMORY.md   |

## Department heads (sold as Department Packs)

| Silo                    | Head               | Members                                                                 |
| ----------------------- | ------------------ | ----------------------------------------------------------------------- |
| Sales                   | `viper-outreach`   | Prospector / Qualifier / Outreach / Follow-Up / Proposal-Writer         |
| Marketing               | `quill-content`    | Calendar / Draft / Repurpose / Schedule / Reply-Inbox                   |
| Marketing (SEO/AEO)     | `sentinel`         | SEO-Auditor / Metadata-Pack / Schema-Pack / AEO-Brief / Competitor-Teardown |
| Engineering             | `codex`            | Scaffold / Implement / Reviewer / Tester / PR-Writer / Docs-Updater     |
| Finance                 | `ops` (ledger sub) | Spend-Watcher / Invoice-Triage / Expense-Coder / Runway / Cost-Optimize |
| Customer Experience     | `consultops`       | Friction-Finder / Unreasonable-Builder / Onboarding-Concierge           |
| Operations / Routing    | `consultops`       | Ingest / Dedup / Route / Notify / Approval-Gate / Anomaly-Detector      |
| Audit / Compliance      | `forge-audit`      | Contract-Metadata / SOC2 / GDPR / RLS-Auditor / Pen-Test                |
| Research / Intelligence | `vanclief`         | Competitor-Watch / Signal-Aggregator / Market-Brief / Deep-Researcher   |

## Specialized profiles

| Profile      | Why standalone                                                         |
| ------------ | ---------------------------------------------------------------------- |
| `lawdbot`    | Mike-Lawdbot Telegram persona; Antfarm 7-step PR pipeline              |
| `mobile`     | Termux edge node — SMS / 2FA / sensors / real-MAC-address social posts |
| `sportsbook` | ML predictions ingestion; EV-threshold monitoring                      |
| `yeh-ops`    | Yehovah trial-to-GA monitoring; ELU friction MCP                       |

## Meta

| Profile    | Role                                                                       |
| ---------- | -------------------------------------------------------------------------- |
| `vanclief` | AI-Expert; weekly brief, monthly research drop, eval auditor, SKU gatekeep |

## How they communicate

- **Inside a tenant:** Hermes built-in delegation + v0.12 Kanban (agents claim tasks from a board, work in parallel).
- **Across tenants / external partners:** Google A2A protocol with JSON Agent Cards published at `agents.prettyflyforai.com/.well-known/agent.json/{tenant}/{sku}`.
- **To external tools:** MCP (stdio + HTTP). Composio MCP is the OAuth bridge for Slack / LinkedIn / Gmail / Calendar.

## Profile-vs-skill rule

A capability gets its own profile only when it has (a) persona-distinct voice, (b) long-running state, (c) channel-isolated identity. Otherwise it's a skill under an existing profile.

Paperclip's 5 muppet roles → 5 profiles (Atlas / Viper / Quill / Forge / Radar) because Claude Max subscription session boundaries must be clean per role.
