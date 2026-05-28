# Slack Block Kit interactive approvals — activation runbook

> Status as of 2026-05-23: **deferred**. PFOS is out of current plans. Treat this runbook as historical until a Hermes-native interactive endpoint exists. Do not configure PFOS/Vercel for Block Kit approvals.

Future direction: replace emoji-reaction polling with Hermes-native webhook-on-click writeback to a local/Hermes approval record. Each Slack button click should write a structured `approval_decision` record, feeding eval pass-rate trends, per-profile trust graduation, and Karpathy ladder promotion gates.

The legacy emoji-reaction path stays alive in parallel until this lands. Don't delete `slack_notify.py::notify_decision` or `scripts/poll-slack-approvals.py` until Block Kit clears one week of live use.

## Why this is gated on Alex

The build shell that scaffolded this had no `SLACK_BOT_TOKEN` exported. Even if it did, two scopes and one workspace setting can only be flipped from the Slack admin UI — not from code:

1. `chat:write` (post Block Kit messages)
2. Slack app's **Interactive Components** endpoint URL configured to a Hermes-owned endpoint
3. `SLACK_SIGNING_SECRET` environment variable on the Hermes-owned endpoint

These are one-way doors: misconfiguring the endpoint URL or signing secret silently breaks delivery without raising an error in the build, so they require human verification.

## Activation steps

Run these in order. Each step is independently reversible; the last one (env flag) is the live-switch.

### 1. Verify current scopes on the bot token

```bash
# In a shell where SLACK_BOT_TOKEN is exported:
curl -sH "Authorization: Bearer $SLACK_BOT_TOKEN" https://slack.com/api/auth.test
# Confirms the token is alive and surfaces the bot_user_id / team_id.

# Then check what scopes the token actually has:
curl -sH "Authorization: Bearer $SLACK_BOT_TOKEN" \
  https://slack.com/api/apps.permissions.scopes.list
```

Required for the Block Kit path:

- `chat:write` — post messages (required)
- `im:write` — open DMs (only if posting to DM channels by user ID rather than pre-resolved `D…` IDs)
- `chat:write.public` — optional, lets the bot post to public channels it isn't a member of

If `chat:write` is missing, request it via the Slack app config UI: **Your Apps → \<app\> → OAuth & Permissions → Scopes → Bot Token Scopes → Add**. Reinstall the app to the workspace to issue a new token, then update `SLACK_BOT_TOKEN` only in the approved Hermes runtime env for the target profile.

### 2. Configure Interactive Components endpoint

In **Your Apps → \<app\> → Interactivity & Shortcuts**:

- Toggle **Interactivity** ON
- Request URL: `<future Hermes-owned Slack interactive endpoint>`
- Save

Slack sends a one-time challenge request to that URL on save. The endpoint will return 503 `{ok: false, reason: "not_enabled"}` until the env flag flips — that's fine; Slack accepts any 2xx/5xx response on the challenge as long as it's not a network error.

### 3. Set the signing secret on the Hermes-owned endpoint

In **Your Apps → \<app\> → Basic Information → App Credentials**, copy **Signing Secret**.

```bash
# Add to the future Hermes-owned endpoint environment.
# Do not add this to PFOS unless Alex explicitly reopens PFOS as an approval surface.
```

For local dev (`pnpm dev`):

```bash
echo 'SLACK_SIGNING_SECRET=<value>' >> .env.local
```

### 4. Flip the enable flag

```bash
vercel env add ENABLE_SLACK_INTERACTIVE production
# value: true
vercel env add ENABLE_SLACK_INTERACTIVE preview
# value: true
```

No PFOS redeploy. Keep this disabled until a Hermes-owned endpoint exists and is explicitly approved.

### 5. Smoke test

From a Hermes-runtime-aware shell with `SLACK_BOT_TOKEN` exported:

```bash
cd ~/Projects/agents
python3 -m hermes.lib.slack_notify \
  "Smoke: Block Kit approval test from $(date +%Y-%m-%d-%H%M%S)" \
  $(python3 -c "import uuid; print(uuid.uuid4())") \
  --block-kit \
  --recipient <D-channel-id-for-alex>
```

You should:

1. See `ts=<slack-message-ts>` printed (the message landed in Slack).
2. See an interactive message in Slack with **Approve / Revise / Reject** buttons.
3. Tap one → message acks with a status change. Check the Hermes approval record store:
   ```bash
   # Example placeholder: query the Hermes approval record for the generated action id.
   ```
   Expect the record store to include the original proposal status change and a sibling `approval_decision` audit record.
4. Tap the same button twice → second click returns 409 `{ok: false, reason: "not_pending"}` — the idempotency guard mirrors `poll-slack-approvals.py`.

### 6. Switch Marin / Stet / Atlas skills to use the Block Kit emitter

Once smoke passes, swap call sites in:

- `hermes/profiles/atlas-ceo/skills/weekly-ceo-brief.md` → swap `notify_decision(...)` for `notify_decision_block_kit(...)`
- `hermes/profiles/marin/skills/weekly-review.md` → same swap
- `hermes/profiles/stet/skills/critique-draft.md` → same swap

Old emoji path remains operational throughout — these swaps are additive, not replacement. After one week of clean Block Kit operation, delete the legacy `notify_decision()` function + `scripts/poll-slack-approvals.py` + the cron entry for the poller.

## Reversal

If anything misbehaves after activation:

```bash
# Disable the Hermes-owned interactive endpoint flag once it exists.
```

The endpoint returns to dormant immediately on next request. Skills that called `notify_decision_block_kit` will silently fall back to logging + returning `None` (per the existing failure-mode contract); upstream skill execution still completes successfully. Switch the skill prose back to `notify_decision` to restore emoji-reaction approvals while debugging.

## Provenance

- Research: `~/Projects/research-vault/research/2026-05-20-agent-fleet-ui-layer-mid-2026.md` § "Move 1"
- Existing emoji path: `hermes/lib/slack_notify.py::notify_decision` + `scripts/poll-slack-approvals.py`
- Webhook endpoint: `prettyfly-os/app/api/slack/interactive/route.ts`
- Block Kit emitter: `hermes/lib/slack_notify.py::notify_decision_block_kit`
