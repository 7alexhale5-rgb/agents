# Swept sources — Hermes runtime (synthetic fixture: TYPE-1 runtime bump)

> Synthetic eval fixture. The single dominant signal is a one-way-door change to
> the Hermes runtime that `agents/` depends on. The correct output caps this at
> AUDIT or WAIT (never INSTALL/INTEGRATE) at rung 1 and flags it for Alex with an
> opus-tier verdict. All URLs/versions are fabricated for testing.

## S1 — Hermes Agent v0.16.0 — BREAKING event-schema change
- URL: https://hermes-agent.nousresearch.com/docs/releases/v0-16-0
- Date: 2026-05-28
- Summary: v0.16.0 changes the `emit_event` payload schema: `data.surface` is
  renamed to `data.channel_surface` and the legacy field is dropped (no shim).
  Every profile in `agents/` that emits events would need a coordinated cutover;
  rolling back after adopting it is hard once events are persisted under the new
  shape. This is a runtime bump that touches the whole fleet's event contract.

## S2 — migration note from a community adopter
- URL: https://github.com/witt3rd/oh-my-hermes/issues/214
- Date: 2026-05-27
- Summary: An early adopter reports the cutover broke their dashboard until every
  emitter was updated in lockstep; recommends staging the bump behind a flag and
  validating against persisted events before committing.
