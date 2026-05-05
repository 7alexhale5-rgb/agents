# Agora bus — event publication contract

> **Status:** Phase 1 substrate primitive (locked 2026-05-05)
> **Backed by:** ADR-003 + decisions #1 / #2 / #11 / #12

The agora is the cross-profile event bus. Concretely it's a single Honcho workspace (`prettyfly-os`) with one peer per Hermes profile. Agents publish events as Honcho messages; auditors (vanclief) read them via the workspace and session search endpoints. There is no HTTP server, no Redis, no "moltbook publishing API" — the bus is the messages a profile is already writing as a side effect of acting.

This doc is the contract. Follow it and your events become readable by every other profile.

## Workspace + session conventions

| Workspace      | Use                                                                      |
| -------------- | ------------------------------------------------------------------------ |
| `prettyfly-os` | Production fleet substrate. Single workspace per operator (decision #2). |

Sessions are buckets within the workspace. Pick one based on traffic shape:

| Session naming          | Use                                                               |
| ----------------------- | ----------------------------------------------------------------- |
| `eval-traces-{YYYY-MM}` | SKU eval trial outcomes. Rolling monthly bucket. Owner: vanclief. |
| `phase-{N}-smoke-test`  | Phase gate verification messages. Idempotent.                     |
| `<sku>-runs-{YYYY-MM}`  | Per-SKU runtime traces (Phase 2+).                                |
| `pain-{YYYY-MM}`        | 4d-senses pain-log events (Phase 4 fold-in).                      |
| `decisions-{YYYY}`      | VanClief Sunday Brief decision items + responses.                 |

Pattern: one session per _kind of event_, dated to keep buckets small (≤10K messages each).

## Event schema (content as JSON string)

Every message's `content` field is a JSON string. The first field is always `event_type`. Add fields as needed; consumers must tolerate unknown extra fields.

```json
{
  "event_type": "eval_trace",
  "sku": "email-triage",
  "provider": "mistral:mistral-medium-latest",
  "date": "2026-05-05",
  "passed": 135,
  "total": 150,
  "rate": 0.9,
  "wilson_lower_ci": 0.8416,
  "manifest_hash": "<sha256>",
  "report_path": "marketplace/manifests/email-triage/eval-suite/reports/..."
}
```

Defined event types so far:

| `event_type` | Producer                                               | Consumer            | Session                 |
| ------------ | ------------------------------------------------------ | ------------------- | ----------------------- |
| `eval_trace` | SKU eval runners (e.g. `email-triage-eval-nightly.sh`) | vanclief, gate-eval | `eval-traces-{YYYY-MM}` |

When you add a new event type, add a row here. Without this row, downstream consumers won't know to read it.

## Producer pattern

Every producer:

1. **Mints an admin JWT.** Honcho auth uses `{"ad": true}` claim signed HS256 with `HONCHO_JWT_SECRET` from `~/Projects/agents/honcho/.env`. Keep the secret out of shell argv — read it from the file in-process or pipe via stdin.

2. **Get-or-creates the session** (idempotent):

   ```
   POST /v3/workspaces/prettyfly-os/sessions  {"id": "eval-traces-2026-05", "peers": {"vanclief": {}}}
   ```

3. **Posts the event message** with `peer_id` set to the producing profile's name and `content` set to the JSON-stringified payload:

   ```
   POST /v3/workspaces/prettyfly-os/sessions/{session}/messages
     {"messages": [{"content": "<json string>", "peer_id": "personal"}]}
   ```

4. **Never breaks the caller.** If the post fails, log it but do not propagate the failure. The substrate is read-mostly; a missed event is recoverable, a broken caller is not.

The reference Python helper is `scripts/honcho-publish-eval-trace.py`. It minimum-viably implements all four steps. New producers either:

- copy and adapt the helper for their event type, or
- shell out to it via `echo '<json>' | scripts/honcho-publish-eval-trace.py`.

**Shebang gotcha:** macOS launchd can resolve a different `python3` than your interactive shell. Pin the shebang to `/usr/bin/python3` for any script that imports `pyjwt` (see `973364a` for the bug that motivated this).

## Consumer pattern

Every consumer:

1. **Mints an admin JWT** the same way as producers (or a workspace-scoped JWT once we issue them).

2. **Reads messages from the session** via the list endpoint:

   ```
   POST /v3/workspaces/prettyfly-os/sessions/{session}/messages/list
     {}                               # empty body returns full session
   ```

3. **Parses each `content` field as JSON** and filters by `event_type`. Tolerate unparseable rows (test fixtures, manual posts).

4. **Filters synthetic providers** out of any aggregate computation. Names beginning with `smoke-test`, `smoke:`, `debug:`, `test:`, `synthetic:` are reserved for path validation, not production gates.

The reference Python consumer is `scripts/vanclief-eval-summary.py`.

## Workspace-wide search

For cross-session discovery, use the workspace-level search endpoint:

```
POST /v3/workspaces/prettyfly-os/search
  {"query": "<text>", "limit": 50}
```

VanClief uses this for the Sunday Brief — gathers eval traces, decision-item responses, and any other event type matching its filter.

## Why this works (and what kills it)

**Decision-#10 forced consumption ratchet.** vanclief's Sunday Brief comes from the agora; if vanclief stops reading the bus, the brief stops being produced; the user notices because the ratchet pause-pings them. The bus has a forced consumer.

**Decision-#5 Wilson-CI gate.** A SKU cannot publish to the marketplace until two distinct providers' eval traces in the agora pass the gate. Producing the trace IS publishing the SKU's evidence. No second hop.

**What kills the bus:**

- Bypassing the substrate ("I'll just write to a file") — the next agent doesn't see it.
- Synthetic events polluting production sessions — filter aggressively.
- Per-event auth tokens (we use a single admin claim today; cross-tenant phase 4.5+ will need scoped tokens — refactor at that boundary, not before).
- Honcho's AGPL drift — keep server-side only (decision #12).

## Quick reference

```
# Publish an eval_trace from a shell script
TRACE_JSON=$(jq -n --arg sku ... '{event_type:"eval_trace", sku:$sku, ...}')
echo "$TRACE_JSON" | scripts/honcho-publish-eval-trace.py || true

# Read the rollup
scripts/vanclief-eval-summary.py
scripts/vanclief-eval-summary.py --json    # machine-readable
scripts/vanclief-eval-summary.py --month 2026-05

# Bootstrap (idempotent — safe to re-run any time)
scripts/honcho-substrate-bootstrap.py

# Repair (only if honcho-api shows password auth failures)
scripts/honcho-db-rotate-password.py
(cd honcho && docker compose up -d --force-recreate honcho-api)
```
