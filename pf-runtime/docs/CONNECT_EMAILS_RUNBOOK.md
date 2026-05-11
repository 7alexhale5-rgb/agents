# Connect emails + calendar — operator runbook

**Goal:** populate all 10 entries in `~/.hermes/profiles/personal/account-registry.yaml` with live credentials so `pf_runtime` can read every Gmail + Calendar + M365 + IMAP mailbox.

**Current state** (run the probe at the bottom of this doc to re-check):

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

3 / 10. The `pf_runtime.oauth.provision` module ships a loopback-redirect provisioner that reduces every account to a single browser click on Google's / Microsoft's consent screen — no OAuth Playground, no curl, no copying access codes by hand.

---

## Step 0 — One-time OAuth-app prep

### 0a — Google: add the loopback redirect URI

1. Open <https://console.cloud.google.com/apis/credentials>.
2. Click the existing OAuth 2.0 Client ID that matches `PF_GOOGLE_OAUTH_CLIENT_ID` in `~/.hermes/profiles/personal/.env`.
3. Under **Authorized redirect URIs** → **+ Add URI** → paste `http://127.0.0.1:8765/callback` → **Save**.

### 0b — Microsoft: register the Azure app

1. Open <https://entra.microsoft.com> → **App registrations** → **+ New registration**.
2. Name: `PrettyFly PF Runtime (personal)`. Supported account types: **Accounts in any organizational directory and personal Microsoft accounts** (multitenant).
3. Redirect URI: **Web** → `http://127.0.0.1:8765/callback`. Click **Register**.
4. Copy the **Application (client) ID**.
5. Sidebar → **Certificates & secrets** → **+ New client secret** → 24-month expiry → copy the **Value** field immediately (Azure hides it after page reload).
6. Sidebar → **API permissions** → **+ Add a permission** → **Microsoft Graph** → **Delegated permissions** → check `Mail.Read`, `Calendars.ReadBasic`, `MailboxSettings.Read`, `offline_access`, `User.Read` → Add.
7. Append three lines to `~/.hermes/profiles/personal/.env`:

   ```
   PF_MS_OAUTH_CLIENT_ID=<application-client-id-from-step-4>
   PF_MS_OAUTH_CLIENT_SECRET=<value-from-step-5>
   PF_GRAPH_REFRESH_TOKEN_KOHO_M365=
   ```

   The refresh-token value is filled in automatically by Step 2. Leave the line blank for now.

---

## Step 1 — Provision the 4 Gmail accounts (4 × ~10 sec each)

Run the provisioner once per account. It opens a browser at Google's consent screen pre-targeted at the right email; click **Allow**; the provisioner writes both the gmail and calendar twin env vars atomically.

```bash
cd ~/Projects/agents/.claude/worktrees/heuristic-satoshi-372cc7/pf-runtime
VENVPY=/Users/alexhale/Projects/agents/pf-runtime/.venv/bin/python

$VENVPY -m pf_runtime.oauth.provision google --account gmail-1 --email alex@prettyflyforai.com --write-also gmail-1-calendar
$VENVPY -m pf_runtime.oauth.provision google --account gmail-2 --email info@prettyflyforai.com --write-also gmail-2-calendar
$VENVPY -m pf_runtime.oauth.provision google --account gmail-3 --email 7alexhale5@gmail.com --write-also gmail-3-calendar
$VENVPY -m pf_runtime.oauth.provision google --account gmail-4 --email alex@ctox.com   --write-also gmail-4-calendar
```

Each command:

- Opens `https://accounts.google.com/o/oauth2/v2/auth?...&login_hint=<email>` in your default browser.
- You click **Allow** (and tap 2FA if Google asks).
- The provisioner's listener captures the redirect, exchanges the code, and writes:
  - `PF_GMAIL_REFRESH_TOKEN_GMAIL_N` (refresh, durable)
  - `PF_GMAIL_TOKEN_GMAIL_N` (access, ~1 hr)
  - `PF_GMAIL_TOKEN_GMAIL_N_CALENDAR` (same access token, for the calendar twin entry)

After step 1: 9 / 10 connected.

---

## Step 2 — Provision koho-m365 (~10 sec)

```bash
$VENVPY -m pf_runtime.oauth.provision microsoft --account koho-m365 --email alex@kohoconsulting.com
```

Single click "Allow" on the Microsoft consent screen. The provisioner writes:

- `PF_GRAPH_REFRESH_TOKEN_KOHO_M365` (refresh, 90 days, rotates)
- `PF_GRAPH_TOKEN_KOHO_M365` (access, ~1 hr)

After step 2: 10 / 10 connected.

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
