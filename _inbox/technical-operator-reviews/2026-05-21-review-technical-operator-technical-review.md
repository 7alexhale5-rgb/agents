---
date: 2026-05-21
type: technical-review
scope: smoke
target: hermes/profiles/technical-operator/skills/technical-review.md
verdict: SHIP-RISK-MEDIUM
door_classification: TYPE-2
findings_count:
  block: 0
  medium: 2
  low: 1
pfos_event_id: ec805034-209a-4515-9010-a525ab1f57ca
---

# Technical Review: technical-review skill (smoke — syntax/structure pass)

> **SMOKE EVIDENCE ONLY.** Scope requested was `smoke`. Per CLAUDE.md line 29,
> smoke-model output is not a production critique. This file is structural/conformance
> evidence only and must not be treated as a final engineering gate. Promote to a
> production-route review before using this as a ship signal.

## Summary

This skill defines the sole procedural workflow for the technical-operator profile: read
one artifact, produce one critique, write it to the inbox, and emit one PFOS event.
The risk surface is the emitter invocation (§ Emit safe event summary) — it shells out
to an external Python script with a secrets env source, and the skill has no explicit
fallback path if the emitter fails mid-write. The verdict turns on whether the emitter
failure mode and the `pfos_event_id` patch step are adequately guarded.

## Verdict: SHIP-RISK-MEDIUM

Door: TYPE-2. The skill file is a documentation artifact; it can be reverted in a
single `git revert` with no data loss and no external side-effect, provided the emitter
has not already written a stale PFOS row.

---

## Findings

### F1 — Emitter failure leaves critique with stale `pfos_event_id: pending` [SHIP-RISK-MEDIUM]

- **Evidence:** `hermes/profiles/technical-operator/skills/technical-review.md:85` (frontmatter field `pfos_event_id: pending`) and line 154 (instruction to patch the field after the emitter runs).
- **Risk:** If the emitter exits non-zero (network error, expired token, schema mismatch), the critique file lands in the inbox with `pfos_event_id: pending` indefinitely. CLAUDE.md line 60 makes the acceptance gate falsifiable via SQL, so a stale `pending` value means the rung-1 gate is never satisfied — the profile appears un-shipped even though the critique file exists. The skill does not define what `pfos_event_id` should be set to on emitter failure, nor whether the critique write is considered complete in that state.
- **Fix shape:** Define the expected failure-mode value for `pfos_event_id` (e.g., `emitter-failed`) and add an explicit exit-code check to the emitter snippet (or a companion note naming the expected behavior). The skill should say whether a critique with `pfos_event_id: emitter-failed` counts as a valid acceptance-gate hit.

### F2 — Hardcoded secrets path not covered by trajectory redaction guard [SHIP-RISK-MEDIUM]

- **Evidence:** `hermes/profiles/technical-operator/skills/technical-review.md:141` — `source ~/.config/prettyfly-marketing/hermes-tokens.env` is hardcoded and unconditional. `config.yaml:30` sets `private_payload_redacted: true` for the PFOS event payload. `config.yaml:76` enables `trajectory_jsonl: true`.
- **Risk:** The `private_payload_redacted` guard applies to the PFOS event row, not to the shell invocation. If the emitter snippet appears verbatim in a trajectory JSONL entry, the secrets file path is logged in plaintext. The path also violates the HERMES_HOME env-var convention stated in AGENTS.md (hardcoded `~/.config/prettyfly-marketing/` instead of `$HERMES_HOME` or a declared env var).
- **Fix shape:** Replace the hardcoded path with an env-var reference consistent with the HERMES_HOME convention, or add an explicit note to the skill stating this snippet is redacted from trajectory logging and citing how that exclusion is enforced.

### F3 — `scope:` parameter accepted but not defined in skill body [SHIP-RISK-LOW]

- **Evidence:** `technical-review.md:4` — frontmatter `input:` field lists `scope:` as optional with no enumeration. CLAUDE.md lines 23–29 partially define `smoke` behavior, but `full`, `diff`, and `risk` are unnamed.
- **Risk:** A caller passing `scope: risk` or `scope: diff` gets no procedure-level guidance on what changes. The skill is the authoritative contract; delegating scope semantics entirely to CLAUDE.md creates a split-source-of-truth for callers who read only the skill file.
- **Fix shape:** Add a brief `## Scope parameter` section to the skill body listing accepted values and which procedure steps each value skips or abbreviates.

---

## Inversion

Assume this shipped 90 days ago and broke catastrophically. The probable cause: the
emitter silently failed on first invocation (expired token or DB partition), left every
critique with `pfos_event_id: pending`, and the rung-1 acceptance gate was treated as
satisfied by visual inspection of the inbox file alone — so the PFOS monitoring signal
was dark from day one and no one noticed the emitter was non-functional until a
downstream consumer tried to query `public.agent_events` and found zero rows.

## Approval gate

To flip this verdict to `SHIP-RISK-LOW`, the following specific evidence must hold:

- F1: The skill (or a runbook it explicitly references) defines what value `pfos_event_id`
  takes on emitter failure and whether a critique in that state counts as a valid
  acceptance-gate hit. A one-line inline note in the emitter snippet block is sufficient.
- F2: The hardcoded `~/.config/prettyfly-marketing/hermes-tokens.env` path is replaced
  with an env-var reference (`$HERMES_TOKENS_ENV` or equivalent), OR a note is added
  explicitly stating this snippet is excluded from trajectory JSONL logging and citing
  the mechanism.
- F3 does not block the flip (SHIP-RISK-LOW severity).
