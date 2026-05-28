---
profile: morning-logs
skill: daily-brief
generated_at: 2026-05-23T22:24:43.802229+00:00
proposal_status: proposed
private_payload_redacted: true
---

# Morning Logs — 2026-05-23-morning-logs

## Operator Answer

- Hermes usable right now: no
- Memory trustworthy today: no
- Gateway: unknown (running: false)
- Broken: gateway not running, Knowledge Vault status unavailable: <urlopen error [Errno 61] Connection refused>, Knowledge Vault retrieval unavailable: <urlopen error [Errno 61] Connection refused>, Knowledge Vault memory health unavailable: <urlopen error [Errno 61] Connection refused>, API usage has 11 warning(s)
- Needs Alex: 0 pending approval(s)
- Recommended next action: Gateway is not running; open Fleet, then Logs, before any workflow work.

## Dashboard Loop

1. Fleet — confirm gateway, approvals, profile roster, and next action.
2. Knowledge Vault — confirm memory freshness, retrieval, and memory-health blockers.
3. Labyrinth — inspect warning guideposts and failed/long journeys.
4. Sessions — open the run transcript only when Labyrinth points there.
5. Logs — inspect raw runtime failures only after Fleet/Labyrinth point there.
6. Cron — confirm Morning Logs schedule and last run.
7. Profiles — verify the responsible profile identity and scope.
8. Config / Keys — use only for setup or broken credentials.
9. Docs — map the API surface for the next narrow slice.

## Fleet

- Pending approvals: 0
- Recent events sampled: 0
- OpenAPI paths visible from `/docs`: 113

## Knowledge Vault

- Freshness ok: false (0 warning(s), 0 failure(s))
- Retrieval eval: unknown (unknown failed)
- Memory health: unavailable (0 blocker(s), 0 warning(s))
- Guardrails: read-only; no reindex, repair, note edit, private vault access, or profile memory-provider mutation.

## API Usage

- Status available: true
- API-billed today: $8.28
- API-billed MTD: $75.84
- Warnings: 11
- Manual reviews overdue: 11
- Degraded providers: none
- Low-balance providers: none
- Operator dashboard: /Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-23-api-usage-dashboard.html

## Labyrinth

- Guideposts: 0
- Warning/error guideposts: 0

## Repos

- agents: ## codex/hermes-webui-first-1-percent...origin/codex/hermes-webui-first-1-percent; dirty files: 72; latest: 46d7b00 feat(hermes): add morning logs workflow
- prettyfly-os: ## main...origin/main; dirty files: 30; latest: c5f1a65 chore(agents): provision technical-operator PFOS row
- memory-vault: ## main; dirty files: 721; latest: 6a49157 session(prettyfly-os): 22:55 update — memory pipeline + wiki-compile shipped

## Safety

- This run did not kill processes, edit tokens, execute approvals, deploy, purchase, or modify repo files.
- PFOS event emission uses only a redacted evidence payload with counts and this report path.
