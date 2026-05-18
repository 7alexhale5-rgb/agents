# CLAUDE.md — `quill-content` profile

> **Profile:** quill-content · **Tier:** TBD · **Channels:** TBD
> **Phase:** TBD

You're inside the quill-content profile. Persona in `SOUL.md`, user in `USER.md`, memory in `MEMORY.md`.

## Per-task routing

| Task | Read | Skills |
| ---- | ---- | ------ |
| TBD  | TBD  | TBD    |

## Model routing

TBD — fill in default / drafting / reasoning / strategic per the org standard.

## Hard rules

1. (per-profile guardrails)

## Acceptance gate

(per-profile success criterion)

## Available MCP tools

`apollo-io` MCP wired via `mcp_servers.apollo-io` in `config.yaml` (source: `~/Projects/apollo-mcp/.env`, wrapper matches `~/.claude.json`). Apollo account is on Professional trial through ~2026-05-29 — converts to paid Pro then. Until conversion, only the 4 enrichment tools below work; the 5 discovery tools return `403 "free plan"`.

For quill-content's research use case, the working tools support: "tell me about this company" (enrich_company), "what is this company hiring for" (job_postings → content angles), and "what news has this company made recently" (news_articles → topical hooks for posts).

| Tool                                    | Status         | Use case                                              |
| --------------------------------------- | -------------- | ----------------------------------------------------- |
| `apollo_enrich_company`                 | ✓ today        | Firmographics by domain                               |
| `apollo_bulk_enrich_organizations`      | ✓ today        | Same, batched                                         |
| `apollo_get_organization_job_postings`  | ✓ today        | Active hires (signal for content angles)              |
| `apollo_search_news_articles`           | ✓ today        | Recent news (topical hooks; needs `organization_ids`) |
| `apollo_search_people`                  | ⏳ ~2026-05-29 | Find people by title/location/company-size            |
| `apollo_search_companies`               | ⏳ ~2026-05-29 | Find companies by industry/size/location              |
| `apollo_enrich_person`                  | ⏳ ~2026-05-29 | Match a person → email + LinkedIn                     |
| `apollo_bulk_enrich_people`             | ⏳ ~2026-05-29 | Same, batched                                         |
| `apollo_get_complete_organization_info` | ⏳ ~2026-05-29 | Full snapshot by org_id                               |

Discovery half flips on automatically at trial conversion — no code change. Reminder lives in `~/.claude/projects/-Users-alexhale-Projects/memory/project_apollo_mcp_trial.md`.
