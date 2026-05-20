---
name: email-triage
description: Read-only email + calendar triage with proposal-only output. Reads inbound mail across Gmail/Microsoft Graph/IMAP HostGator, applies per-silo rules, computes priority + filing labels, extracts calendar events from message bodies, and writes proposed actions to a local store. Never sends mail, never accepts meetings — proposes only.
---

# Skill: email-triage

Use this when a Hermes profile needs to triage inbound communications (email + calendar) across multiple accounts and surface high-priority items + filing proposals + calendar-event candidates without taking external action.

## Status

**Salvaged from `pf-runtime/pf_runtime/communications/` 2026-05-19** during the $1M-pivot cleanup. Code is preserved here as the canonical home; Python-package integration into a Hermes profile loop happens when `koho-ops` or `yeh-ops` (Phase 5 of `~/.claude/plans/here-is-what-we-joyful-torvalds.md`) goes to invoke it.

Until then, treat this skill as **reference + reusable building blocks**, not a live skill the runtime loads.

## Inputs

- Per-account credentials (Gmail OAuth, Microsoft Graph OAuth, or IMAP password)
- `triage-rules.yaml` per silo — VIP senders, role hints, never-flag-as-urgent overrides
- An account registry mapping email address → silo + provider + scopes

## Procedure (when integrated)

1. Resolve the account from the registry (`account_registry.py`); enforce read+propose scopes only (`policy.py`).
2. Fetch new messages since last sync (`clients/gmail.py`, `clients/graph.py`, `clients/imap_hostgator.py`).
3. Normalize to `NormalizedMessage` schema (`schema.py`, `providers.py`).
4. Apply silo rules (`rules.py`): role match, sender VIP, role hint.
5. Compute priority (`priority.py`) and filing label (`filing.py`).
6. Map to silo (`silo_map.py`) for routing.
7. Extract calendar candidates from message body (`calendar_extraction.py`); cross-check with `clients/google_calendar.py` for conflicts.
8. Write proposed actions to the local proposal store (`proposal_store.py`). Never send, accept, decline, or modify externally.

## Output shape

A `ProposedAction` row per actionable message, with: `action_type`, `target_resource`, `confidence`, `evidence_refs`, `proposed_at`. Profiles read the store and surface proposals through their channel; the human approves before any external action.

## Hard constraints

- **Read + propose only.** No write paths. Scope assertions in `clients/__init__.py` and `policy.py` fail loudly if a write-capable scope is requested.
- **No raw message text in PFOS payloads** (per ADR `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`). Emit safe operational summaries only.
- **Per-account `.env` for credentials** — no shared-runtime credential store. Each profile owns its account creds.

## Files

| Path                               | Role                                                                                             |
| ---------------------------------- | ------------------------------------------------------------------------------------------------ |
| `rules.py`                         | `SiloRules`, `first_role_match`, `sender_is_vip`, `TriageRules`, `RoleHint`                      |
| `filing.py`                        | `suggest_label`                                                                                  |
| `priority.py`                      | `compute_priority`                                                                               |
| `silo_map.py`                      | `silo_for_address`                                                                               |
| `calendar_extraction.py`           | Calendar-event extraction from message body                                                      |
| `schema.py`                        | `NormalizedMessage`, `TriageBucket`, `Provider`, `AccountConfig`, `ActionType`, `ProposedAction` |
| `account_registry.py`              | `AccountRegistry`, `RegistryEntry`, scope enforcement                                            |
| `proposal_store.py`                | `ProposalStore` — local SQLite-backed store of proposed actions                                  |
| `policy.py`                        | `assert_v1_action_allowed` — defense-in-depth scope check                                        |
| `providers.py`                     | Provider-side normalization helpers                                                              |
| `sync_state_store.py`              | `SyncState`, `SyncStateStore` — per-account sync cursor                                          |
| `cli.py`                           | Standalone CLI helpers (`_format_run_result_json` etc.) — kept for tests only                    |
| `clients/gmail.py`                 | Gmail REST client (stdlib `urllib`)                                                              |
| `clients/graph.py`                 | Microsoft Graph client (stdlib `urllib`)                                                         |
| `clients/imap_hostgator.py`        | HostGator IMAP client (stdlib `imaplib`)                                                         |
| `clients/google_calendar.py`       | Google Calendar read client                                                                      |
| `oauth/google.py`                  | Google OAuth refresh + token lifecycle                                                           |
| `oauth/microsoft.py`               | Microsoft OAuth refresh + token lifecycle                                                        |
| `oauth/provision.py`               | Interactive OAuth provisioner (one-time per account)                                             |
| `config/triage-rules.example.yaml` | Sample silo rules config                                                                         |
| `docs/CONNECT_EMAILS_RUNBOOK.md`   | Operator runbook for connecting an account                                                       |
| `tests/`                           | 13 test files + `fixtures/classifier_regression.jsonl`                                           |

## Known integration gaps

The following imports in this code currently resolve to the archived `pf_runtime/` namespace and must be rewritten when the skill is integrated:

| Symbol                                              | Old path                                  | Fix path                                                                                       |
| --------------------------------------------------- | ----------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `from pf_runtime.communications.X import Y`         | archived                                  | `from email_triage.X import Y` (after re-homing under `email_triage/` Python package)          |
| `from pf_runtime.communications.clients.X import Y` | archived                                  | `from email_triage.clients.X import Y`                                                         |
| `from pf_runtime.oauth.X import Y`                  | archived                                  | `from email_triage.oauth.X import Y`                                                           |
| `from pf_runtime.config import load_profile`        | runtime-bound                             | Replace with profile-config loader from the consuming Hermes profile                           |
| `from pf_runtime.runtime.model_adapter import ...`  | runtime-bound                             | Replace with Hermes model adapter from the consuming profile                                   |
| `from pf_runtime.runtime.pfos_emit import ...`      | runtime-bound                             | Stub or replace with Hermes-PFOS event emit per ADR `2026-05-18-hermes-pfos-event-contract.md` |
| `triage_skill.py`, `tools.py` (NOT salvaged)        | runtime-bound orchestrator + tool wrapper | Rebuild against the consuming profile's tool interface                                         |

The pure-functional modules (`rules.py`, `priority.py`, `filing.py`, `silo_map.py`, `calendar_extraction.py`, `schema.py`, `policy.py`) are runtime-agnostic and need only import-rewriting.

## Acceptance gate for integration

The skill is integration-complete when:

1. A Hermes profile (`koho-ops` or `yeh-ops`) can invoke this skill's pipeline against one real account
2. `proposal_store.py` writes at least one `ProposedAction` row for a real inbox message
3. The profile's channel surfaces that proposal for human approval
4. Zero raw message text leaks into PFOS `agent_events` payloads (per the event contract)
5. All non-runtime-bound tests in `tests/` pass

## References

- Plan that birthed this code: `~/Projects/research-vault/research/2026-04-25-realtime-ai-sales-coach-prettyfly-os.md`
- $1M pivot that archived its original home: `~/.claude/plans/here-is-what-we-joyful-torvalds.md`
- Event contract for safe PFOS emission: `_meta/decisions/2026-05-18-hermes-pfos-event-contract.md`
- Original launchd config (archived, not active): `_archive/2026/pf-runtime/launchd/com.prettyfly.pf-triage.plist`
