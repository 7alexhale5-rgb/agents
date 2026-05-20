# email-triage — salvaged skill

This skill carries the email + calendar triage logic salvaged from the archived `pf-runtime/pf_runtime/communications/` tree on 2026-05-19.

**See `SKILL.md` for the invocation contract.**

## Why this lives here

The 2026-05-18 $1M pivot archived `pf-runtime/`. The triage code inside it had genuine revenue-pipeline value — Koho retainer (Marc lead intake), Yehovah retainer (trial-to-GA monitoring). Rather than lose it to the archive, we lifted it here so Phase 5 of the $1M plan (`koho-ops`, `yeh-ops` profile builds) can adopt it directly.

## Provenance

- Original: `pf-runtime/pf_runtime/communications/` + `pf-runtime/pf_runtime/oauth/` on branch `claude/triage-fixes-phase-5`
- Last commits before salvage:
  - `6609f2d` — `fix(extraction): accept 3-letter weekday abbreviations`
  - `2c8dc5f` — `fix(triage): derive IMAP host from account address`
  - `6adc627` — `feat(triage): Phase 5 calendar correlation + gmail 404 race fix`
  - `5a2ac7c` — `PF Runtime: OAuth provisioner + email/calendar connect (10/10)`
- Salvage commit: this one
- Branch retired after salvage: `claude/triage-fixes-phase-5`

## State today

- **Files are byte-identical copies** of the originals — no import rewriting yet.
- **Tests will not pass as-is** — they import from `pf_runtime.communications.*` which is archived. See `SKILL.md` § Known integration gaps for the rewrite map.
- **Pure-functional modules** (`rules.py`, `priority.py`, `filing.py`, `silo_map.py`, `calendar_extraction.py`, `schema.py`, `policy.py`) need only path rewriting.
- **Runtime-bound modules** (orchestrator, tool wrapper, PFOS emit, model adapter) were intentionally not salvaged — they're rebuilt against the consuming profile when integration happens.

## What got dropped during salvage

Files in `pf-runtime/pf_runtime/communications/` we deliberately did not copy here:

- `triage_skill.py` — orchestrator that binds to the PF Runtime loop. Rebuild against the consuming Hermes profile's run loop.
- `tools.py` (`CreateProposalTool`) — wraps the proposal store as a runtime tool. Rebuild against the consuming profile's tool interface.

Both reference runtime-level abstractions that don't exist outside `pf-runtime/`.

## Integration checklist (for whoever builds koho-ops or yeh-ops)

1. Re-home Python under `hermes/shared-skills/email-triage/email_triage/` and add `__init__.py` files
2. Mass-rewrite imports per `SKILL.md` § Known integration gaps
3. Write a thin orchestrator inside the consuming profile that wires `fetch_new → normalize → triage → proposal_store.write`
4. Wire the proposal store output to the profile's channel surface (Slack DM, dashboard, etc.)
5. Use `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md` for any PFOS event emission — never raw text
6. Run the test suite; expect the runtime-bound tests (`test_cli_scheduled.py`, `test_pfos_emit_phase2.py`, parts of `test_proposal_store_dedupe.py`) to need stubs or refactoring
