# CLAWS roles mapped to PF Runtime + Hermes ports

**Source:** Gravity Claw five-way split (Connect / Listen / Archive / Wire / Sense), lifted into Phase 4.7 per [`PIVOT_2026-05-06.md`](../../.planning/phase-4-7-prettyfly-runtime/PIVOT_2026-05-06.md) §2.

**Convention:** CLAWS names are **runtime subsystems**, not separate Slack users. Iris stays one outward bot persona.

| CLAWS role  | Responsibility                                                       | PF Runtime component(s) (current / planned)                                            | Hermes v0.12.0 reference to port                                     |
| ----------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Connect** | Authenticate to channels; maintain Socket Mode / OAuth lifetimes     | `pf_runtime.channels.slack.SlackChannel.connect()`; registry in `channels/__init__.py` | Gateway plugins + Slack adapter                                      |
| **Listen**  | Ingest user events; normalize to `InboundMessage`; thread continuity | `Channel.receive()` → `gateway._handle_inbound`; DM + `thread_ts` metadata             | `gateway` ingress + session attribution                              |
| **Archive** | Durable session + message history; recall across restarts            | `BufferStore` (Tier 2 SQLite); future: Hermes-compatible session DB / reset policy     | `hermes_state.py` SessionDB, `SessionResetPolicy` (pivot §2 catalog) |
| **Wire**    | Tool / MCP dispatch, provider calls, idempotency                     | `run_session` + `OpenRouterAdapter`; future: `tool_dispatch.py`, MCP clients           | `agent/auxiliary_client.py`, tool runner                             |
| **Sense**   | Telemetry, hooks, cost/latency signals, operator alerts              | Future: Langfuse + audit sink per `TRACE_SCHEMA.md`; reconnect logging in `gateway.py` | Langfuse tracing, trajectory JSONL                                   |

## Failure modes (operator-facing)

| Role    | Symptom                      | First check                                                |
| ------- | ---------------------------- | ---------------------------------------------------------- |
| Connect | No "connected" log           | Bot + app tokens in profile `.env`; Keychain / launchd env |
| Listen  | DMs dropped                  | User ID allowlist; DM vs channel routing in Slack adapter  |
| Archive | No cross-session memory      | Buffer path writable; profile slug non-empty               |
| Wire    | Auth errors or empty replies | `OPENROUTER_API_KEY` in per-profile `.env`                 |
| Sense   | Blind flight                 | Trace export; gateway stderr log                           |

## Related docs

- [`ADAPTER_PLUGIN_INTERFACE.md`](ADAPTER_PLUGIN_INTERFACE.md) — reconnect + idempotency
- [`MEMORY_LIFECYCLE.md`](MEMORY_LIFECYCLE.md) — tier boundaries
- [`STATUS.md`](../../.planning/phase-4-7-prettyfly-runtime/STATUS.md) — pivot sub-phase C/E status
