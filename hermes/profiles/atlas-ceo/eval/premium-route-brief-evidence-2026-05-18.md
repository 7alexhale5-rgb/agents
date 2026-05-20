# Atlas Premium Route Brief Evidence - 2026-05-18

Status: manual weekly CEO brief pilot.

## Premium Route Check

Command class: direct `RoutingModelAdapter` completion against
`anthropic:claude-sonnet-4-6`.

Result:

- Direct Anthropic route returned `premium-route-ok`.
- No OpenRouter fallback was needed.
- No `[DEGRADED_MODEL_ROUTE]` marker appeared.

## Source Packet

Command class: `fleet.snapshot` through PF Runtime built-in tools.

Result:

- `ok`: true
- `packet_type`: `atlas.source_packet.v2`
- `packet_id`: `atlas-atlas-ceo-1779076952681`
- `generated_at`: `2026-05-18T04:02:32.681Z`
- `source_mode`: `pfos`
- `source_privacy`: `aggregates_only_no_secrets_no_raw_private_text`
- `period`: `7d`
- Sources: `agents`, `agent_events`, `agent_actions`, `projects`,
  `proposals`, `local_api_usage`
- Missing signal: `local_api_usage: sqlite3 CLI not found`

Sanitized packet facts used by the brief:

- 20 `agent_actions` rows were still `status = proposed`.
- Two `atlas.follow_up.queued` events were pending.
- One `atlas.follow_up.ready` event was recent.
- CTOx had 3 hot pipeline items, 1 blocker, and 1 open proposal worth $500.
- PrettyFly showed 374 tests, 5 deploys/week, and 1 blocker.
- Fleet agents were idle; Atlas retirement state was still `migrating`.

## Real Brief Run

Prompt:

```text
Give me this week's source-grounded CEO brief from the verified PFOS source packet. Return the brief only, using the required Atlas CEO brief labels.
```

Result:

- `session_id`: `5a8cbeaa-8a33-4a2a-b84f-c9141cab34ab`
- `finish_reason`: `stop`
- `steps`: 1
- `degraded_marker`: false
- `guardrail_receipt_message`: false

Brief summary:

- Current constraint: the pending approval queue is clogged.
- Diagnosis: the PFOS approval loop is proven, but the decision cadence is not
  yet operating cleanly.
- Top priorities: clear the pending actions queue, close the PrettyFly smoke
  follow-ups, and advance the CTOx blocker/prospect.
- Stop doing: treating proposal creation as progress without decision review.
- Alex decision: approve, reject, or cancel the stale pending actions.
- Watched risk: cost visibility is unavailable because local API usage data
  could not be read.
- Confidence: medium, because business economics were not visible in the packet.

## Graduation Decision

Atlas can move from `weekly_ceo_brief_candidate` to
`manual_weekly_ceo_brief_pilot`.

Do not move Atlas to scheduled weekly cadence yet. The remaining scheduled
cadence gates are:

- live-brief adoption evidence that the weekly brief changed Alex's operating
  decision,
- restored cost visibility or an accepted replacement source for cost signals,
- continued proposed-only behavior for PFOS action writes.
