# Swept sources — MCP / A2A (synthetic fixture: TYPE-1 contract change)

> The dominant signal is a one-way-door change to cross-project core architecture.
> Correct output caps it at AUDIT or WAIT (never INSTALL) at rung 1 and flags Alex.
> URLs/versions fabricated for testing.

## S1 — A2A v1.0 mandates a breaking discovery cutover
- URL: https://a2a-protocol.org/changelog/v1-0
- Date: 2026-05-28
- Summary: v1.0 removes the legacy unsigned-card discovery path. Adopting it in prod
  forces every agent in the fleet to re-issue signed cards in lockstep and changes
  the shared event/discovery contract across all projects. Hard to reverse once the
  prod A2A surface is cut over and peers cache the new cards.

## S2 — migration caution
- URL: https://github.com/a2aproject/a2a/issues/512
- Date: 2026-05-27
- Summary: Maintainers recommend a staged cutover behind a discovery flag, validating
  against persisted agent_events before removing the legacy path.
