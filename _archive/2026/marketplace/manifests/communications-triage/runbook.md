# Runbook — communications-triage

## Bootstrap (one-time)

1. Copy the example registry into the profile dir:

   ```bash
   mkdir -p ~/.hermes/profiles/personal
   cp marketplace/manifests/communications-triage/account-registry.example.yaml \
     ~/.hermes/profiles/personal/account-registry.yaml
   ```

2. Edit it to list real accounts. Read-only scopes only — the loader
   refuses any forbidden_v1 scope at load time.

3. Provision env vars in `~/.hermes/profiles/personal/.env`. One token
   per account; the env-var name follows
   `<PROVIDER_PREFIX><ACCOUNT_ID_UPPER_UNDERSCORE>`:

   ```sh
   # PFOS observability (POST target on the PFOS Vercel deploy)
   PFOS_AGENT_EVENT_URL=https://os.prettyflyforai.com/api/silos/fleet/agent-event
   PFOS_AGENT_EVENT_TOKEN=<32-byte hex bearer token>
   PFOS_AGENT_EVENT_REQUIRE_HTTPS=1

   # Per-account credentials (pre-issued OAuth access tokens / IMAP password)
   PF_GMAIL_TOKEN_GMAIL_1=<oauth2 access token>
   PF_GMAIL_TOKEN_GMAIL_2=<oauth2 access token>
   PF_GRAPH_TOKEN_KOHO_M365=<oauth2 access token>
   PF_IMAP_PASSWORD_YEHOVAH_HOSTGATOR=<imap password>
   ```

   Run `bash scripts/pf-cutover-preflight.sh` from the agents repo to
   audit env presence and surface missing accounts.

4. Mint the PFOS bearer token (one-time, Alex-ops, in PFOS Supabase SQL
   editor):

   ```sql
   -- Generate a fresh hex token, capture it client-side:
   SELECT encode(gen_random_bytes(32), 'hex') AS fleet_token;
   -- Insert its sha256 hash with agent_events:write scope:
   INSERT INTO public.agent_tokens (company_id, token_sha256, scope, note)
   VALUES (
     (SELECT id FROM public.companies LIMIT 1),
     encode(digest('<paste hex from step 1>', 'sha256'), 'hex'),
     ARRAY['agent_events:write'],
     'pf_runtime-communications-triage'
   );
   ```

   Set the plaintext token as `PFOS_AGENT_EVENT_TOKEN` in the profile
   `.env`. Revoke later with
   `DELETE FROM public.agent_tokens WHERE note = 'pf_runtime-communications-triage'`.

## Daily operation

```bash
# Run a triage pass against all credentialed accounts.
python -m pf_runtime comms triage

# Limit to one account.
python -m pf_runtime comms triage --account gmail-1

# Review what was proposed.
python -m pf_runtime comms proposals list

# Drill into a single proposal.
python -m pf_runtime comms proposals show gmail-1-msg123-reply_draft

# Approve or reject (v1: local DB only, no provider mutation).
python -m pf_runtime comms proposals approve gmail-1-msg123-reply_draft
python -m pf_runtime comms proposals reject gmail-1-msg123-reply_draft
```

Each triage run emits a `pf_runtime_triage_start` and matching
`pf_runtime_triage_end` `STATE_CHANGED` event to PFOS, plus one
`pf_runtime_proposal` `ARTIFACT_CREATED` event per proposal and
`pf_runtime_triage_error` `ERROR` events for any per-account failure.
Surface:`pf_runtime`. agent_slug:`personal`. skill_slug:`communications-triage`.

Filter on PFOS: Fleet silo → `FleetSkillsGrid` → "communications-triage".

## Kill switch

Disable the profile or connector account before investigating:

```bash
touch ~/.hermes/profiles/personal/PAUSED
```

To disable PFOS emission only (keeps triage running, just stops writing
agent_events): `unset PFOS_AGENT_EVENT_URL` (or remove from .env).

## Red incidents

- Any email sent without approval.
- Any mailbox mutation applied without approval.
- Any calendar event created, changed, or deleted without approval.
- Any connector requesting a forbidden v1 write/send scope.

Response: halt the profile, revoke the affected provider token, inspect
`communications_proposals`, and add a regression test before re-enabling.

## Diagnosis log tokens

`journalctl` / log-aggregator queries:

| Token                           | Meaning                                                           |
| ------------------------------- | ----------------------------------------------------------------- |
| `PFRT_TRIAGE_START`             | Run kicked off (run_id, accounts_with_creds)                      |
| `PFRT_TRIAGE_END`               | Run finished (proposals, errors, duration_ms)                     |
| `PFRT_ACCOUNT_FETCH_START`      | Per-account fetch starting                                        |
| `PFRT_ACCOUNT_FETCH_END`        | Per-account fetch summary (fetched, classified, proposed)         |
| `PFRT_ACCOUNT_FETCH_ERROR`      | Per-account fetch failure (exception class)                       |
| `PFRT_CLASSIFY_FAIL`            | Classifier returned non-conforming output                         |
| `PFRT_NORMALIZE_FAIL`           | Single-message normalization failure (warning, account continues) |
| `PFRT_GMAIL_HISTORY_ID_EXPIRED` | Gmail historyId 404 → full resync                                 |
| `PFRT_GRAPH_DELTA_GONE`         | Graph deltaLink 410 → full resync                                 |
| `PFRT_IMAP_UIDVALIDITY_CHANGED` | IMAP UIDVALIDITY changed → full resync                            |
