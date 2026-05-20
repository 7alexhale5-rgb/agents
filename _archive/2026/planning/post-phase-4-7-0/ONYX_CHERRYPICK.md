---
date: 2026-05-11
status: in-progress (§1 shipped; §2-§4 deferred)
source_repo: onyx-dot-app/onyx (29.3k stars, MIT)
target: pf-runtime/pf_runtime/
---

# Onyx → PF Runtime cherry-pick plan

After reading Onyx's `backend/onyx/connectors/interfaces.py` and `connectors/gmail/connector.py`, four patterns are worth stealing. Ranked by pain × proximity to where PF Runtime hurts today.

## What we're NOT stealing (and why)

- `Document` / `Section` / `HierarchyNode` / `ExternalAccess` models — Onyx is building a hybrid search index over documents; PF Runtime is building a triage queue with proposals. Different output shape, different consumer.
- `SlimConnector*` / `*WithPermSync` variants — these support per-document permissioning for multi-tenant deployments. PF Runtime is single-tenant (alex).
- `IndexingHeartbeatInterface` — Celery progress callback. We don't have Celery yet.
- Vespa + Postgres + Redis + MinIO stack — wrong memory model for PF Runtime's tier-based (working/episodic/semantic/procedural) memory.

## §1 — Refreshable Google credentials [SHIPPED 2026-05-11 on main]

**Onyx ref:** `backend/onyx/connectors/interfaces.py::CredentialsProviderInterface` + `connectors/google_utils/google_auth.py::get_google_oauth_creds`.

**Gap closed:** Codex's `clients/gmail.py` and `clients/google_calendar.py` take a raw `access_token: str` (line 53 in each). Google access tokens expire in 60 minutes. Today's path: paste fresh token into `.env`, hope you finish your work before it stales, repeat. We hit this on tonight's smoke (gmail-1 401).

**Shape:** `pf_runtime/oauth/google.py` — stdlib-only (no `google-auth` dep added, matches `model_adapter.py` style).

- `RefreshableGoogleCredentials.from_env(account_id, profile="personal")` — loads `PF_GOOGLE_OAUTH_CLIENT_ID`, `PF_GOOGLE_OAUTH_CLIENT_SECRET`, `PF_GMAIL_REFRESH_TOKEN_<ACCOUNT>` from profile `.env`.
- `.get_access_token()` — returns cached token if more than 60s remain on its life, else refreshes via `oauth2.googleapis.com/token`.
- `.refresh()` — explicit refresh, writes record to `~/.hermes/profiles/<profile>/oauth-cache/<account_id>.json` (mode 0600).
- `write_access_token_to_env(profile, account_id, token)` — replaces the `PF_GMAIL_TOKEN_<ACCOUNT>` line in profile `.env` so existing Codex clients keep working unchanged.
- CLI: `python -m pf_runtime.oauth.google refresh --account gmail-1 --profile personal` — refreshes one account, updates `.env`, exits 0.

**Operator runbook for one-time refresh-token provisioning** (per account):

1. Open https://developers.google.com/oauthplayground in a browser logged into the target account.
2. Top-right gear → "Use your own OAuth credentials" ON → paste your own client_id + client_secret (from console.cloud.google.com → APIs & Services → Credentials → OAuth 2.0 Client IDs → Web application). Add `https://developers.google.com/oauthplayground` as an authorized redirect URI.
3. Top-right gear → "Force prompt: consent" ON, "Use HTTPS" ON, "Offline access" ON.
4. Step 1: paste scopes (e.g. `https://www.googleapis.com/auth/gmail.readonly`), click Authorize APIs, sign in.
5. Step 2: Exchange authorization code for tokens. The right panel now shows BOTH `access_token` AND `refresh_token`.
6. Set in profile `.env`: `PF_GOOGLE_OAUTH_CLIENT_ID=...`, `PF_GOOGLE_OAUTH_CLIENT_SECRET=...`, `PF_GMAIL_REFRESH_TOKEN_<ACCOUNT>=...` (refresh token).
7. Run `python -m pf_runtime.oauth.google refresh --account <id>` whenever a fresh access token is needed.

**Acceptance:** 8 unit tests pass with no network calls; live smoke after operator provisioning runs `comms triage` without 401.

**Cron candidate** (Phase 2 of this cherry-pick): launchd job runs `refresh` for all accounts every 45 minutes; eliminates manual rotation entirely.

---

## §2 — Checkpoint-based resumable pagination [DEFERRED — needs Codex's PR merged first]

**Onyx ref:** `interfaces.py::ConnectorCheckpoint` + `CheckpointedConnector.load_from_checkpoint(start, end, checkpoint)` + Gmail's `GmailCheckpoint(user_emails, page_token)`.

**Gap:** PF Runtime's `communications_sync_state` schema has the right provider cursors (`history_id`, `delta_link`, `last_uid`/`uid_validity`) for _post-completion_ state. But mid-run pagination state isn't captured — if a sync over 1000 messages dies at message 500, the next run starts from the previous successful run's cursor and re-fetches the first 500.

**Onyx's pattern:**

- `PAGES_PER_CHECKPOINT = 1` — each invocation processes one page, returns the new checkpoint.
- Caller persists the checkpoint between batches; resumes by reloading it.
- Checkpoint is a typed Pydantic model — different per connector but all have `has_more: bool`.

**Cherry-pick:** add `checkpoint_json TEXT` column to `communications_sync_state`. Define `pf_runtime.communications.checkpoint.BaseCheckpoint(BaseModel)` with `has_more` + provider-specific subclasses. Modify `_triage_account` to loop on checkpoint until `has_more=False`, persisting between iterations.

**Why deferred:** touches `schema.py`, `triage_skill.py`, and all four `clients/*.py` — exactly Codex's open slice. Land this after `codex/email-triage-access-completion` merges.

**Estimated LOC:** ~120 (schema migration + base checkpoint model + 3 provider subclasses + 3 client modifications + 2 tests).

---

## §3 — `PollConnector` ABC [DEFERRED — same conflict surface as §2]

**Onyx ref:** `interfaces.py::BaseConnector` → `PollConnector.poll_source(start, end)`.

**Gap:** Codex's `clients/gmail.py`, `graph.py`, `imap_hostgator.py`, `google_calendar.py` are bespoke shapes. Each has its own connection setup, retry, error handling. Adding a new provider (say Discord or GitHub issues) costs more than it should.

**Cherry-pick:** define `pf_runtime.communications.connector.PollConnector(ABC)` with `load_credentials(creds: dict) -> dict | None` and `poll_source(start: float, end: float) -> Iterator[NormalizedMessage]`. Refactor the four existing clients to implement it. Builds toward §2 (the checkpoint pattern overlays cleanly on `PollConnector`).

**Why deferred:** refactor of Codex's `clients/*.py`. Wait until his PR merges.

**Estimated LOC:** ~80 LOC for the ABC + ~50 LOC per client modification = ~280 total.

---

## §4 — Shared retry wrapper [DEFERRED — minor; can land standalone post-merge]

**Onyx ref:** `connectors/gmail/connector.py:50` — `add_retries = retry_builder(tries=50, max_delay=30)` decorator. Uses exponential backoff on `HttpError`s with rate-limit/transient status codes.

**Gap:** PF Runtime clients likely have ad-hoc retry (or none). Live smoke worked first try so we haven't seen the failure mode yet, but Gmail's 429 rate limit at 250 quota units/user/sec is real.

**Cherry-pick:** `pf_runtime.communications.retry::retry_with_backoff(tries=10, base_delay=1.0, max_delay=30.0)` decorator. Apply to network-bound methods in each client.

**Why deferred:** trivial, but the apply-points are all in Codex's tree. Easier to land in one slice with §3.

**Estimated LOC:** 30 LOC for the decorator + a few `@retry_with_backoff` lines.

---

## Sequencing

```
shipped:    §1 RefreshableGoogleCredentials (main @ <commit>)
                ↓ (operator provisions refresh tokens once)
                ↓
                ↓ (Codex's codex/email-triage-access-completion → main)
                ↓
next slice:  §3 PollConnector ABC + §4 retry wrapper (single PR, ~310 LOC)
                ↓
                ↓
next-next:   §2 Checkpoint-based pagination (~120 LOC, requires §3 base)
                ↓
                ↓
follow-up:   Refresh-token cron (launchd → `python -m pf_runtime.oauth.google refresh` every 45min)
                ↓
                ↓
beyond:      §1 second-mover — Microsoft Graph refreshable credentials (same shape, different token URL)
```

## Open questions / forward-looking

- Should the refresh helper auto-detect missing client_id/secret and walk operator through OAuth Playground setup? (Probably yes, in a `provision` subcommand.)
- Should the cache live in `~/.hermes/profiles/<p>/oauth-cache/` (per-profile) or `~/.hermes/oauth-cache/` (global)? Currently per-profile to match the `.env` scope. Revisit if cross-profile re-use becomes useful.
- Onyx also has a `CredentialsConnector` interface for credentials that mutate mid-run (locking). Single-tenant PF Runtime probably never needs this — note for posterity.
