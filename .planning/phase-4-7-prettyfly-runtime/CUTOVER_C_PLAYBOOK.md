---
phase: 4.7
sub_phase: C
title: Slack adapter live cutover for personal — operator playbook
status: ready (await sub-phase C build complete + smoke green)
date_authored: 2026-05-06
operator: alex
---

# Sub-phase C cutover playbook

This is the procedure that swaps Iris on Slack from Hermes (v0.12.0 pinned) to PF Runtime
for the `personal` profile. It is operator-gated. Do not execute any step below until:

1. Sub-phase C build is complete (Channel ABC + SlackChannel + gateway daemon + tests).
2. Local dry-run smoke (5+ DMs against PF Runtime daemon, manual terminal) is green.
3. You have an empty 24-hour window where you can monitor without being away from a laptop.

## What this cutover does

| Before                                         | After                                                                  |
| ---------------------------------------------- | ---------------------------------------------------------------------- |
| `ai.hermes.gateway-personal` runs Hermes Slack | `ai.prettyfly.pf-runtime-personal` runs PF Runtime Slack               |
| Personal Slack DMs answered by Hermes v0.12.0  | Personal Slack DMs answered by PF Runtime sub-phase C build            |
| Memory tiers via Hermes SQLite + FTS5 + Honcho | Memory tiers via PF Runtime BufferStore (Tier 2) + SoulReader (Tier 1) |
| LiteLLM + auxiliary_client.py provider chain   | OpenRouterAdapter direct (single provider; no fallthrough)             |

Sub-phases D and E (dream loop, Kanban, additional channels) layer on top
_after_ this cutover holds for 14 days.

## Pre-cutover gates (do not start without all green)

- [ ] `cd ~/Projects/agents/pf-runtime && .venv/bin/python -m pytest tests/ -v` — 100% pass (19 tests as of 2026-05-06)
- [ ] `cd ~/Projects/agents/pf-runtime && .venv/bin/ruff check pf_runtime tests` — clean
- [ ] `cd ~/Projects/agents/pf-runtime && .venv/bin/mypy pf_runtime` — clean
- [ ] Manual dry-run completed: stop Hermes daemon, run PF Runtime manually, send 5+ DMs to Iris, verify replies arrive within 5 seconds and feel coherent
- [ ] You have a clear 24-hour observation window (no travel, no other deploys)
- [ ] Hermes profile state files at `~/.hermes/profiles/personal/{state.db,sessions/,gateway_state.json}` are backed up (these are not used by PF Runtime; the backup is for rollback evidence only)

### Repo-only verification (maintainer automation; optional checkpoint)

Record here when the slice is green before operator launchd steps:

| Check                                                            | 2026-05-06 session |
| ---------------------------------------------------------------- | ------------------ |
| `pip install -e ".[dev,channels,runtime]"` in `pf-runtime/.venv` | Green              |
| `pytest tests/`                                                  | 19 passed          |
| `ruff check pf_runtime tests`                                    | Pass               |
| `mypy pf_runtime`                                                | Pass               |

**Operator steps (launchd):** still required — this table does not replace manual DM smoke or token checks in per-profile `.env`.

## Step 1 — Stop Hermes (graceful)

```bash
launchctl unload ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist
sleep 5
ps aux | grep -E "hermes_cli.*gateway" | grep -v grep
# Should be empty. If not, find the PID and SIGTERM it manually.
```

Verify Iris stops responding:

```bash
# In Slack: send "ping" to @iris. No reply expected within 30 seconds.
```

## Step 2 — Promote the staged plist

```bash
mv ~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist.staged \
   ~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist

# Sanity-check it
plutil -lint ~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist
# expected: "OK"
```

## Step 3 — Pre-flight the PF Runtime daemon manually

Before launchctl-loading, run the daemon in the foreground for 60 seconds and verify
it reaches "[SlackChannel] connected" without crashing.

```bash
cd ~/Projects/agents/pf-runtime
./.venv/bin/python -m pf_runtime gateway --profile personal
# Watch for:
#   "[SlackChannel] connected as bot=U... profile=personal"
# Send one DM to Iris in Slack. Observe a reply.
# Ctrl-C the daemon.
```

If the dry-run does not connect or does not reply, **roll back to step 0** and do not
proceed. Reload Hermes:

```bash
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist
```

## Step 4 — Load the PF Runtime launchd job

```bash
launchctl load -w ~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist
sleep 5
launchctl list | grep ai.prettyfly.pf-runtime-personal
# Expect: PID present, exit code "-" (running)
```

Tail the log:

```bash
tail -f ~/.hermes/profiles/personal/logs/pf-runtime.log &
tail -f ~/.hermes/profiles/personal/logs/pf-runtime.error.log &
```

## Step 5 — Smoke (immediate)

Send 5 test DMs to @iris in Slack:

1. "ping" → expect a non-empty reply
2. "what's my name?" → expect a name (Tier 2 buffer hydration test)
3. "what color did I tell you was my favorite?" → tests cross-session memory; should
   recall from buffer if you've answered this before in PF Runtime
4. "tell me one thing about your role" → tests Tier 1 SOUL.md injection
5. A message with an image attached → expect a reply (sub-phase C ignores attachments;
   that's fine — confirm no crash)

If any of the 5 fails or the daemon crashes:

```bash
launchctl unload ~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist
# investigate; do not retry the cutover the same day
```

## Step 6 — 50-DM 24-hour smoke window

This is the cutover gate. Send (or have natural traffic produce) 50 DMs to @iris over
the next 24 hours. Track in a simple log:

| Metric                           | Threshold              | How to measure                                                            |
| -------------------------------- | ---------------------- | ------------------------------------------------------------------------- |
| Unhandled exceptions             | 0                      | `grep -c Traceback ~/.hermes/profiles/personal/logs/pf-runtime.error.log` |
| Duplicate sends                  | 0                      | manual inspection of Slack thread; also `grep dedup` in log               |
| p95 reply latency                | ≤ 2000 ms              | timestamps in `pf-runtime.log`; or Langfuse traces                        |
| Reply correctness (subjective)   | "felt right" on ≥45/50 | judgment call                                                             |
| Memory hydration across restarts | Tier 2 buffer survives | restart the daemon mid-window; verify next reply remembers                |

If any threshold breaks, **roll back** (step 7) and do not retry until the cause is
fixed and re-tested.

## Step 7 — Rollback (if smoke fails)

```bash
launchctl unload ~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist
launchctl load ~/Library/LaunchAgents/ai.hermes.gateway-personal.plist
sleep 5
launchctl list | grep ai.hermes.gateway-personal
# Verify Hermes is back. Send a Slack DM to confirm.
```

The Hermes profile state at `~/.hermes/profiles/personal/state.db` was untouched by
PF Runtime (PF Runtime writes to `pf_buffer.sqlite` in the same directory but never
reads or writes `state.db`), so Hermes should resume cleanly.

## Step 8 — Post-cutover housekeeping (only if smoke is green)

Once the 24-hour window clears:

- [ ] Mark sub-phase C complete in `.planning/phase-4-7-prettyfly-runtime/PIVOT_2026-05-06.md`
- [ ] Commit the staged → real plist promotion (the `.staged` rename) in your dotfiles
      repo if you version-control LaunchAgents
- [ ] Start sub-phase D build (DreamLoop + Tier 4 SkillRegistry)
- [ ] Add a memory entry (auto-memory) noting cutover date + smoke metrics

## What NOT to do during the 24-hour window

- Do not deploy other personal-profile changes (memory tier modifications, model
  swaps, etc.). One change at a time.
- Do not run `~/Projects/agents/scripts/sync-profile.sh push personal` — both Hermes
  and PF Runtime read `~/.hermes/profiles/personal/`, and a config change mid-window
  would muddy the signal.
- Do not load any plist in `~/Library/LaunchAgents/ai.hermes.*` — you'd run two
  agents against the same Slack tokens and Socket Mode would race.

## Concurrent-Hermes safety net

Slack Socket Mode tolerates only one active app-token connection at a time. If you
accidentally have both `ai.hermes.gateway-personal` and
`ai.prettyfly.pf-runtime-personal` loaded, Slack will rotate which one receives each
event and you will see flaky double-replies or missed replies. Always:

```bash
launchctl list | grep -E "ai\.(hermes\.gateway|prettyfly\.pf-runtime)-personal"
# Should show exactly ONE entry, never both.
```

## Open questions / known gaps in sub-phase C

- Tool dispatch (LAIK MCP, file operations) is not yet wired — `tools=[]` in run_session.
  Replies will be conversational only; if a DM asks Iris to do something tool-bound
  (read a file, look up a spec, call an MCP), the reply will be a polite refusal or
  a generic answer. This lands in sub-phase D.
- DreamLoop (post-session async reflection) is not yet running — no skill self-gen,
  no episodic memory write-back. Sub-phase D.
- Kanban store is not yet wired — inbound dedup is in-memory only. If the daemon
  crashes hard mid-session, the inbound message_id may not survive process restart;
  Slack will redeliver, and the in-memory dedup is fresh, so the same message can
  produce a duplicate reply. **Mitigation during sub-phase C window**: don't crash
  the daemon. KeepAlive will restart it but inbound state is lost. If you see one
  duplicate reply, this is the known cause; sub-phase E (Postgres Kanban) fixes it.
- Multi-workspace, threads, file uploads, slash commands, approval buttons are all
  out of scope for sub-phase C. DM-only.

## Reference: file inventory shipped in sub-phase C

- `pf_runtime/channels/__init__.py` — registry self-registration
- `pf_runtime/channels/adapter_base.py` — Channel ABC + ChannelRegistry + errors
- `pf_runtime/channels/slack.py` — SlackChannel concrete adapter
- `pf_runtime/runtime/gateway.py` — long-running daemon + reconnect loop
- `pf_runtime/__main__.py` — extended CLI with `gateway` subcommand
- `tests/test_channel_registry.py`
- `tests/test_channel_abc_lifecycle.py`
- `tests/test_slack_channel.py`
- `tests/test_gateway_reconnect.py`
- `~/Library/LaunchAgents/ai.prettyfly.pf-runtime-personal.plist.staged` (rename to remove `.staged` at cutover)
- This playbook
