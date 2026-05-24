---
profile: morning-logs
skill: daily-brief
generated_at: 2026-05-22T13:06:45.451743+00:00
proposal_status: proposed
private_payload_redacted: true
---

# Morning Logs — 2026-05-22-morning-logs

## Operator Answer

- Hermes usable right now: no
- Memory trustworthy today: no
- Gateway: startup_failed (running: false)
- Broken: gateway not running, slack: Slack app token already in use (PID 98985). Stop the other gateway first., Memory health has 3 blocker(s), 16 recent runtime error marker(s)
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
- OpenAPI paths visible from `/docs`: 95

## Knowledge Vault

- Freshness ok: true (0 warning(s), 0 failure(s))
- Retrieval eval: 10/10 (0 failed)
- Memory health: needs attention (3 blocker(s), 4 warning(s))
- Guardrails: read-only; no reindex, repair, note edit, private vault access, or profile memory-provider mutation.
- Strict-wiki blocker: wiki/ableton-mcp.md: source newer than last_compiled: <local-path>
- Strict-wiki blocker: wiki/graph-health.md: source newer than last_compiled: memory-command-center.md
- Strict-wiki blocker: wiki/graph-health.md: source newer than last_compiled: vaults/index.md

## Labyrinth

- Guideposts: 0
- Warning/error guideposts: 0

## Repos

- agents: ## codex/hermes-webui-first-1-percent...origin/codex/hermes-webui-first-1-percent; dirty files: 11; latest: 46d7b00 feat(hermes): add morning logs workflow

## Safety

- This run did not kill processes, edit tokens, execute approvals, deploy, purchase, or modify repo files.
- PFOS event emission uses only a redacted evidence payload with counts and this report path.
