# Changelog - marin

## 2026-05-18

- Scaffold validated against the Atlas-shaped profile contract.
- Added Phase 1.7 Marin runtime/event contract references.
- Added `generate-handoff` as the shared handoff skill.
- Added eval fixtures for continue / narrow / rewrite / pause weekly decisions.
- Dogfooded first AI Ops Audit weekly readout into the marketing inbox.
- Emitted live PFOS evidence event `93018557-e7b3-477b-a6a3-24c7db209c79` for `marin.weekly_decision.proposed`.
- Passed Phase 2 product gate: Alex confirmed the first readout's `continue, hold volume, wait for route` judgment was accurate.
- Added Marin-owned `buyer-signal-router` skill with routing fixtures for no-reply, accepted, positive, correction, referral, negative, and stop-request states.
- Hardened the Marin promotion gate with field-level buyer-signal-router eval assertions and local promotion evidence in `eval/marin-promotion-evidence-2026-05-18.md`.
- Added `supervised-dispatch` as a packet-only LinkedIn dispatch skill with daily cap, weekly cap, live-session requirement, and account-health stop conditions.
