---
profile: morning-logs
skill: daily-brief
generated_at: 2026-05-24T16:24:58.161507+00:00
proposal_status: proposed
private_payload_redacted: true
---

# Morning Logs — 2026-05-24-morning-logs

## Operator Answer

- Hermes usable right now: yes
- Memory trustworthy today: yes
- Gateway: running (running: true)
- Broken: nothing blocking in the collected signals
- Needs Alex: 17 pending approval(s)
- Recommended next action: Review oldest pending approval: cmo weekly-review (107.65h).

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

- Pending approvals: 17
- Recent events sampled: 10
- OpenAPI paths visible from `/docs`: 113
- Oldest approval: cmo / weekly-review (107.65h, cmo.weekly_decision.proposed)

## Knowledge Vault

- Freshness ok: true (1 warning(s), 0 failure(s))
- Retrieval eval: 10/10 (0 failed)
- Memory health: clean with known warnings (0 blocker(s), 1 warning(s))
- Guardrails: read-only; no reindex, repair, note edit, private vault access, or profile memory-provider mutation.
- Freshness warning: obsidian index is stale (1h-24h old)

## API Usage

- Status available: true
- API-billed today: $0.00
- API-billed MTD: $84.13
- Warnings: 0
- Manual reviews overdue: 0
- Degraded providers: none
- Low-balance providers: none
- Operator dashboard: /Users/alexhale/Projects/memory-vault/operator-artifacts/2026-05-24-api-usage-dashboard.html

## Labyrinth

- Raw guideposts visible: 13
- Actionable warning/error guideposts: 0
- Historical/remediated guideposts remain visible in Labyrinth but are not Morning Logs blockers.

## Repos

- agents: ## codex/hermes-webui-first-1-percent...origin/codex/hermes-webui-first-1-percent [ahead 5]; dirty files: 4; latest: adc36e2 docs(hermes): define active slack gateway policy
- prettyfly-os: ## main...origin/main; dirty files: 30; latest: c5f1a65 chore(agents): provision technical-operator PFOS row
- memory-vault: ## main; dirty files: 1042; latest: 265191a carl: phase 2 rule-effectiveness eval + dedupe cascade prune

## Safety

- This run did not kill processes, edit tokens, execute approvals, deploy, purchase, or modify repo files.
- PFOS event emission uses only a redacted evidence payload with counts and this report path.
