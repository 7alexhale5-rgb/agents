# Connect emails + calendar — operator runbook

**Goal:** populate all 10 entries in `~/.hermes/profiles/personal/account-registry.yaml` with live credentials so `pf_runtime` can read every Gmail + Calendar + M365 + IMAP mailbox.

**Current state** (run `python -c "..." | …` from this doc's footer to re-check):

```
[OK  ] gmail-1            google_mail       alex@prettyflyforai.com
[MISS] gmail-1-calendar   google_calendar   alex@prettyflyforai.com
[MISS] gmail-2            google_mail       info@prettyflyforai.com
[MISS] gmail-2-calendar   google_calendar   info@prettyflyforai.com
[MISS] gmail-3            google_mail       7alexhale5@gmail.com
[MISS] gmail-3-calendar   google_calendar   7alexhale5@gmail.com
[OK  ] gmail-4            google_mail       alex@ctox.com
[MISS] gmail-4-calendar   google_calendar   alex@ctox.com
[MISS] koho-m365          microsoft_graph   alex@kohoconsulting.com
[OK  ] yehovah-hostgator  imap_hostgator    alex@yehovahbuilders.com
```

3 / 10. Steps below take it to 10 / 10.

---

## Step 1 — Re-consent the 4 Gmail accounts with combined scopes

The two existing Gmail refresh tokens were minted with `gmail.readonly` only. Calendar needs `calendar.events.readonly` granted at consent time — same OAuth flow, additional scope, single refresh token covers both.

**Same procedure for each of gmail-1 .. gmail-4.** Combined scope string (paste into OAuth Playground Step 1):

```
https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.events.readonly https://www.googleapis.com/auth/calendar.freebusy
```

1. Open <https://developers.google.com/oauthplayground> in a browser logged into the target account (sign in/out at <https://accounts.google.com> if you have multiple).
2. Top-right gear → **Use your own OAuth credentials = ON** → paste the existing client_id + client_secret already in `~/.hermes/profiles/personal/.env` (`PF_GOOGLE_OAUTH_CLIENT_ID` / `PF_GOOGLE_OAUTH_CLIENT_SECRET`). The Authorized redirect URI for this client must include `https://developers.google.com/oauthplayground` — verify once at <https://console.cloud.google.com/apis/credentials>.
3. Top-right gear → **Force prompt: consent = ON**, **Use HTTPS = ON**, **Offline access = ON**.
4. Step 1 (left panel): paste the combined scope string above → click **Authorize APIs** → sign in + grant consent.
5. Step 2: click **Exchange authorization code for tokens**. The right panel now shows `access_token` + **`refresh_token`** — capture the refresh_token.
6. Open `~/.hermes/profiles/personal/.env` and set/replace the matching `PF_GMAIL_REFRESH_TOKEN_GMAIL_N` line with the new refresh token. For gmail-2 and gmail-3 these lines don't exist yet — append them.
7. Mint a fresh access token (and populate the calendar twin env var atomically):

   ```bash
   cd ~/Projects/agents/.claude/worktrees/heuristic-satoshi-372cc7/pf-runtime
   /Users/alexhale/Projects/agents/pf-runtime/.venv/bin/python -m pf_runtime.oauth.google \
       refresh --account gmail-N --profile personal \
       --write-also gmail-N-calendar
   ```

   Repeat for N = 1, 2, 3, 4. Each run rewrites both `PF_GMAIL_TOKEN_GMAIL_N` (gmail client) and `PF_GMAIL_TOKEN_GMAIL_N_CALENDAR` (calendar client) from one refresh token. Cached at `~/.hermes/profiles/personal/oauth-cache/gmail-N.json` (mode 0600).

**Expected outcome after step 1:** 8 entries OK in the registry (4 gmail + 4 calendar + the 1 already-good gmail-4 + yehovah-hostgator carried over). Only `koho-m365` still missing.

---

## Step 2 — Connect koho-m365 (Microsoft Graph)

The `pf_runtime/oauth/microsoft.py` module mirrors the Google flow: same env-var contract, same `.env` rewrite pattern, with two MS-specific behaviors — Microsoft rotates the refresh token on every exchange (handled automatically), and the tenant is configurable via `PF_MS_OAUTH_TENANT_ID` (defaults to `common`).

### 2a — Register an Azure AD app (~5 min, one-time)

1. Open <https://entra.microsoft.com> → App registrations → **+ New registration**.
2. Name: `PrettyFly PF Runtime (personal)`. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts** (multitenant). Redirect URI: **Public client/native (mobile & desktop)** → `https://login.microsoftonline.com/common/oauth2/nativeclient`.
3. Hit **Register**. Copy the **Application (client) ID**.
4. Sidebar → **Certificates & secrets** → **+ New client secret** → 24-month expiry → copy the **Value** column immediately (Azure hides it after page reload).
5. Sidebar → **API permissions** → **+ Add a permission** → **Microsoft Graph** → **Delegated permissions** → check `Mail.Read`, `Calendars.ReadBasic`, `MailboxSettings.Read`, `offline_access`, `User.Read` → Add.
6. (Optional but recommended) **Grant admin consent for <your tenant>** — only if alex@kohoconsulting.com is the tenant admin.

### 2b — Capture a refresh token via the browser auth-code flow

1. Open this URL in a browser logged in as `alex@kohoconsulting.com` (replace `{CLIENT_ID}` with the Application ID from 2a step 3):

   ```
   https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id={CLIENT_ID}&response_type=code&redirect_uri=https%3A%2F%2Flogin.microsoftonline.com%2Fcommon%2Foauth2%2Fnativeclient&response_mode=query&scope=Mail.Read%20Calendars.ReadBasic%20MailboxSettings.Read%20offline_access%20User.Read&prompt=consent
   ```

2. Complete sign-in + consent. The browser redirects to `https://login.microsoftonline.com/common/oauth2/nativeclient?code=…`. Copy the entire `code=` query param value (everything after `code=` up to `&session_state` or the end).

3. Exchange the code for tokens (replace `{CLIENT_ID}`, `{CLIENT_SECRET}`, `{AUTH_CODE}`):

   ```bash
   curl -s -X POST https://login.microsoftonline.com/common/oauth2/v2.0/token \
     -d "client_id={CLIENT_ID}" \
     -d "client_secret={CLIENT_SECRET}" \
     -d "grant_type=authorization_code" \
     -d "code={AUTH_CODE}" \
     -d "redirect_uri=https://login.microsoftonline.com/common/oauth2/nativeclient" \
     -d "scope=Mail.Read Calendars.ReadBasic MailboxSettings.Read offline_access User.Read" \
     | python3 -m json.tool
   ```

   Response contains `access_token` (~1 hr), `refresh_token` (90 days, rotates), `expires_in`.

### 2c — Populate `.env` and verify

Append/edit the following in `~/.hermes/profiles/personal/.env`:

```
PF_MS_OAUTH_CLIENT_ID={CLIENT_ID}
PF_MS_OAUTH_CLIENT_SECRET={CLIENT_SECRET}
PF_GRAPH_REFRESH_TOKEN_KOHO_M365={REFRESH_TOKEN from step 2b}
# Optional — restrict to Koho's tenant. Default "common" works fine.
# PF_MS_OAUTH_TENANT_ID={kohoconsulting-tenant-guid}
```

Then verify the refresh flow works:

```bash
cd ~/Projects/agents/.claude/worktrees/heuristic-satoshi-372cc7/pf-runtime
/Users/alexhale/Projects/agents/pf-runtime/.venv/bin/python -m pf_runtime.oauth.microsoft \
    refresh --account koho-m365 --profile personal
```

(The `cd` is required while the OAuth modules live on the worktree branch — once
this merges to main, the canonical `pf-runtime/.venv/` install picks them up
and the explicit cd goes away.)

Expected output: `refreshed koho-m365: token updated in profile .env, expires in 3599s (refresh_token rotated)`. The CLI rewrites both `PF_GRAPH_TOKEN_KOHO_M365` (access) and `PF_GRAPH_REFRESH_TOKEN_KOHO_M365` (the rotated value).

---

## Step 3 — Confirm 10 / 10

Re-run the live probe (paste at any time):

```bash
/Users/alexhale/Projects/agents/pf-runtime/.venv/bin/python - <<'PY'
import sys, os
sys.path.insert(0, '/Users/alexhale/Projects/agents/.claude/worktrees/heuristic-satoshi-372cc7/pf-runtime')
from pathlib import Path
from pf_runtime.communications.account_registry import AccountRegistry

env_path = Path.home() / ".hermes" / "profiles" / "personal" / ".env"
for raw in env_path.read_text().splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    if line.startswith("export "): line = line[7:].strip()
    k, v = line.split("=", 1)
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

reg = AccountRegistry.load(
    Path.home() / ".hermes" / "profiles" / "personal" / "account-registry.yaml",
    env=os.environ,
)
for e in reg.entries:
    flag = "OK  " if e.credentials_present else "MISS"
    print(f"  [{flag}] {e.account.account_id:<22} {e.account.provider.value:<18} {e.account.address}")
print(f"\nConnected: {sum(1 for e in reg.entries if e.credentials_present)} / {len(reg.entries)}")
PY
```

When all 10 read `[OK  ]`, the read+propose surface is fully wired. Next: design the triage system (separate session).

---

## Refresh-token hygiene

- **Google** tokens don't expire (until revoked) — once captured they're stable.
- **Microsoft** tokens last 90 days but **rotate on every refresh**. The CLI writes the new refresh token back to `.env` and to `~/.hermes/profiles/personal/oauth-cache/koho-m365.json` (mode 0600) so a CLI crash mid-exchange is recoverable from the cache.
- **HostGator** uses an IMAP password, no rotation.

Access tokens cache for 60s less than their lifetime and auto-refresh on the next `get_access_token()` call.
