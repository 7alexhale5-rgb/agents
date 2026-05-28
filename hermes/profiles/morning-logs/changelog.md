# changelog — morning-logs

## 2026-05-23 — API budget/health read path

Added read-only API usage status from `~/.api-usage/latest.json` to the daily brief. Morning Logs may surface totals, warnings, manual-review debt, degraded provider names, and the operator dashboard path, but never raw keys or provider payloads.

## 2026-05-22 — Morning Logs v0.1

Initial read-only/propose-only Hermes operations profile.

- Fleet as front door
- Knowledge Vault as memory trust surface
- Labyrinth as trace/debug surface
- local report output to `_inbox/morning-logs/`
- safe event type `morning_logs.report.proposed`
- no dangerous controls
