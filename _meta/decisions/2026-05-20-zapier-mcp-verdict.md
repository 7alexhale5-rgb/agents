---
date: 2026-05-20
type: decision
status: active
tags: [mcp, zapier, gmail, outbound, drafts, decision]
parent_plan: ~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md
related_adrs:
  - 2026-05-18-hermes-pfos-event-contract.md
  - 2026-05-20-honcho-peer-card-atlas.md
supersedes: none
---

# Zapier MCP for Gmail draft creation — Verdict: LIMITED-SCOPE

## Decision

Adopt Zapier MCP for Gmail **draft creation only**, scoped to **one profile (Marin) as a pilot**, with a separate Zapier MCP server per brand and a strict server-side action allow-list that includes only the Gmail "Create Draft" action. Do not extend to Quill / Stet / Atlas until the Marin pilot clears the acceptance gate (4 weekly readouts with zero unintended sends and zero cross-brand leakage).

Hard-blocked surfaces on every Zapier MCP server we create:

- Action allow-list contains only `Gmail: Create Draft`. No "Send Email", no "Reply", no "Forward". Verified in the Zapier UI before the server URL is generated.
- One Gmail connection per MCP server. One MCP server per brand. The Zapier account hosting the server has only that one Gmail connection authorized for that server's app scope.
- Server URL stored in the per-profile `.env` (chmod 600), never in repo.

## Context

The propose-only doctrine says agents draft, humans send. Marin's `outreach-pilot` (and Quill's content drafts, later) need a path from "draft text in agent memory" to "draft visible in Gmail UI for human review and one-click send". The existing Hermes email infrastructure (`hermes/shared-skills/email-triage/`) is intentionally read-only — its `account_registry.py` refuses any account that requests `gmail.modify` scope or SMTP-send on IMAP, by design. There is no green-field outbound path today.

Per the parent plan, Phase 4.8 is a verdict on whether Zapier MCP is the right primitive to fill that gap, or whether to pick a different layer.

The brand-credential isolation rule (memory: `feedback_brand_credential_isolation.md`) is a hard constraint: brand A's Gmail credentials must never surface in brand B's project context.

## Alternatives considered

### 1. Zapier MCP — selected (LIMITED-SCOPE)

**What it is.** Zapier-hosted MCP servers expose a configurable subset of Zapier's 9,000+ app actions to MCP clients (Claude, Cursor, custom agents). Authentication is per-MCP-server-instance via Zapier's normal OAuth app connections.

**Evidence:**

- Pricing: MCP is available on all Zapier plans including Free. 1 MCP tool call consumes 2 Zapier tasks from the plan's quota. (Source: zapier.com/mcp, zapier.com/mcp/email, 2025–2026)
- Action whitelisting: documented per-MCP-server. "Customize the specific actions your AI assistant can perform" — each MCP server has its own action allow-list. (Source: zapier.com/mcp product pages)
- Auth: each Gmail connection is OAuth-granted to the Zapier account, and the MCP server URL is per-server-instance. Multiple Gmail accounts can connect to one Zapier account; the per-server config picks one connection per action.
- Data retention (Zap Content, which MCP calls inherit): 7 days in logs, 29–69 days in account, up to 4 months in backups. Configurable shorter on Company/Enterprise plans. (Source: zapier.com/legal/data-retention-deletion, 2025)

**Pros:**

- Setup time ~15–30 minutes per brand: create Zapier account (or sub-account), authorize one Gmail connection, build MCP server with one allowed action, drop the URL into the profile's `.env`. No code to write or maintain on our side.
- Drafts-only enforced server-side by Zapier's UI before the URL is generated. If "Send Email" is not in the allow-list, the MCP client cannot invoke it — the tool simply isn't exposed.
- Per-brand isolation via separate Zapier accounts is operationally clean and Alex-auditable (one account per brand, one Gmail per account).
- TYPE-2 reversible: revoke the OAuth grant, delete the MCP server, remove the URL from `.env`. Done.

**Cons:**

- Email body content flows through Zapier's infrastructure and lands in Zap Content storage (7d logs / 29–69d account / 4mo backups). Acceptable for draft creation of outbound prospecting / content (which is not customer PII) but would be unacceptable for inbound or sensitive content.
- The Gmail-specific "Create Draft" vs "Send Email" action separation is documented as user-controllable per MCP server but the exact action names are not enumerated in Zapier's MCP-specific docs — must be verified in the Zapier UI before the pilot ships. (See pilot prerequisite below.)
- 2 tasks per MCP call inflates Zapier task consumption ~2x vs. equivalent Zaps. Marin's projected volume (one weekly readout × 5–15 draft creations) is well within the Free tier's typical 100-task allowance.

### 2. Composio Gmail MCP — REJECTED

**Why rejected.** Per Composio's 2025–2026 public docs, none of the hard requirements have documented answers:

- Drafts-only tool exposure: not documented (no published config for hiding `send_email` while exposing `create_draft`).
- Per-brand isolation: per-user vs per-org scoping for Gmail not clearly documented.
- Self-hosting Gmail MCP: not documented as a supported option (the hub that brokers auth is Composio-hosted).
- Data retention for Gmail content specifically: not documented at the granularity Zapier provides.

"Not documented" on every hard requirement is itself a verdict. Revisit if Composio publishes a Gmail-MCP-specific security/retention page.

### 3. Google Workspace MCP (community / de-facto) — DEFERRED FALLBACK

**Why deferred.** No official Google-branded MCP Gmail server exists as of 2026-05. The community reference is the `modelcontextprotocol/servers` Gmail implementation (or equivalents). Trade-offs:

- Self-hosted = full control over data flow (no third-party storage of email bodies), zero monthly cost, full per-brand isolation by running one server instance per brand with one OAuth token each.
- BUT: no built-in drafts-only mode flag; would require a small wrapper or fork to expose only `create_draft`. Maintenance burden on Alex.
- Setup time ~4–8h per brand (Google Cloud Console OAuth client, token storage, server deployment, isolation hardening).

**Use case:** if the Marin Zapier pilot fails (unexpected cost, drafts-only verification doesn't hold, retention concerns escalate), fall back to this. The wrapper to expose only `create_draft` is ~40 LOC of FastAPI in front of `googleapiclient.discovery.build('gmail', 'v1').users().drafts().create()`.

### 4. Manual SMTP / extend the existing email-triage infra — REJECTED FOR NOW

**Why rejected.** The existing `hermes/shared-skills/email-triage/` is IMAP-read-only by hard design — `account_registry.py` refuses `gmail.modify` scope and SMTP-send. Extending it to support drafts means either (a) adding the Gmail API drafts endpoint as a new transport in `clients/`, which contradicts the v1 read+propose-at-the-configuration-boundary doctrine the existing module was built to enforce, or (b) building a parallel send-side module.

Either path is 8–16h of green-field work for a capability Zapier MCP gives us in 30 minutes. Not the right time to invest the build cost when a TYPE-2 reversible alternative exists.

**Revisit condition:** if email volume crosses ~500 drafts/month per brand (Zapier task quota strain) or if outbound content becomes sensitive enough that retention via third-party infra becomes a real risk.

### 5. Magica (magica.com) — REJECTED (wrong primitive)

**Why rejected.** Magica is an AI media/LLM workflow orchestration platform — its 23 MCP tools are workflow CRUD (`create_workflow`, `add_node`, `start_run`, `get_balance`, etc.) and direct media generation (`execute_tool`, `upload_file`, `get_generations`). Zero email, Gmail, drafts, or outbound messaging tools. Magica is an AI generation pipeline runner, not a SaaS integration broker. (Source: magica.com/docs/mcp-server/tools, magica.com/docs/llms.txt, 2026-05-20)

**Worth a separate evaluation for a different question** — Magica's workflow orchestration + media generation could be relevant for Quill/Stet content production pipelines (image generation, video for marketing, batched LLM steps). That's a Phase 4.5+-tier separate decision, not this one. Flagged for the capability roadmap.

### 6. Do nothing — REJECTED

Marin's outreach loop is approval-blocked until the propose path reaches Alex's Gmail inbox. Keeping the status quo means Marin's rung 3 graduation stalls. The capability gap is real and load-bearing on Phase 4.7's downstream value.

## Decision framework score

| Criterion                              | Weight | Zapier MCP                 | Composio | GWS MCP (self-host) | Manual SMTP | Magica |
| -------------------------------------- | ------ | -------------------------- | -------- | ------------------- | ----------- | ------ |
| Drafts-only scope supportable          | hard   | yes (server allow-list)    | unknown  | yes (with wrapper)  | yes         | n/a    |
| Per-brand credential isolation         | hard   | yes (separate accounts)    | unknown  | yes (separate srvs) | yes         | n/a    |
| Cost (3-yr)                            | medium | $0 free tier covers Marin  | unknown  | $0 + Alex's time    | $0 + time   | n/a    |
| Setup time per brand                   | medium | 15–30 min                  | unknown  | 4–8h                | 8–16h       | n/a    |
| Lock-in risk                           | medium | low (Gmail OAuth portable) | medium   | none                | none        | n/a    |
| Doctrine fit (propose-only, brand iso) | high   | strong with allow-list     | unclear  | strong with wrapper | strongest   | n/a    |
| Data retention of email content        | medium | 7d–4mo via Zapier          | unknown  | 0 (self-hosted)     | 0           | n/a    |
| Maintenance burden                     | medium | near-zero                  | medium   | medium-high         | high        | n/a    |

**Outcome buckets** (per plan):

- Adopt: hard requirements met + ≥4 medium criteria → fleet rollout
- Limited-scope: hard requirements met + 2–3 medium criteria → pilot on ONE profile
- Skip: any hard requirement fails OR ≤1 medium criteria

Zapier meets both hard requirements and 6 of 7 medium criteria — technically meets the Adopt threshold. The LIMITED-SCOPE downgrade is policy, not framework arithmetic: the drafts-only action separation needs UI verification before fleet trust, and the per-brand pattern wants a 4-readout observation window before scaling.

## Pilot prerequisite (before any code or `.env` change)

Alex (or Claude under live operator) must verify in the Zapier UI:

1. Create a fresh Zapier MCP server.
2. Under "Choose Actions", confirm the Gmail app exposes "Create Draft" and "Send Email" as distinct, independently selectable actions.
3. Add ONLY "Create Draft". Do NOT add "Send Email".
4. Generate the server URL and confirm the MCP client (test with `curl` or Claude session) sees `gmail_create_draft` and does NOT see `gmail_send_email`.

If step 2 reveals that Gmail's MCP actions don't separate at this granularity, halt the pilot and fall back to Alternative 3 (community Gmail MCP server with custom drafts-only wrapper).

## Implementation plan if pilot prerequisite holds

Out of scope for this ADR. Phase 4.8.1 will land a file-level plan covering:

- Marin profile `tools.builtin` entry (`marin.gmail_create_draft` shim wrapping the Zapier MCP tool)
- `tools.contracts` declaration with `proposed_write_only` authority and event block (`marin.gmail_draft.proposed`)
- Per-brand `.env` slot for the Zapier MCP server URL
- Eval fixture validating contract emission shape

## Reversibility

TYPE-2. Per-brand rollback procedure:

1. Revoke the Gmail OAuth grant in the Zapier account.
2. Delete the Zapier MCP server.
3. Remove the URL from the profile's `.env`.
4. Remove the `marin.gmail_create_draft` entry from `marin/config.yaml` (or set `tools.contracts.<name>.enabled: false`).
5. `bash scripts/sync-profile.sh push marin`.

No accumulated state on our side. Zap Content in Zapier's logs ages out per their retention schedule (≤4 months in backups).

## Acceptance (4-readout pilot gate)

After Marin runs 4 weekly readouts with the Zapier MCP draft path active, all of these must hold:

1. Every draft Marin creates lands in the right brand's Gmail Drafts folder. Zero cross-brand leaks.
2. Zero accidental sends (the allow-list scoping holds across all 4 weeks).
3. `marin.gmail_draft.proposed` event row appears in `public.agent_events` for every draft, with `data_runtime=hermes`, `data_proposal_status=proposed`, `data_target_gmail_account=<hashed account ID>`.
4. Zapier task consumption stays inside the Free tier (i.e., under ~100 tasks/month, equivalent to ~50 MCP calls).
5. Alex audits the drafts and notes ≥1 case where the draft was actually one-click-sendable without editing — the value test.

If any of (1)–(3) fails, halt and roll back. If (4) fails (tier strain), upgrade Zapier plan or migrate to Alternative 3. If (5) fails (drafts are never good enough to send), the failure is upstream of this ADR — fix Marin's drafting quality, not the transport.

After acceptance, propose Phase 4.8.2 to extend to Quill (content drafts) and Stet (critique drafts).

## Cost watch

- Zapier Free tier: 100 tasks/month per account, no time limit.
- Marin projection: 1 weekly readout × 5–15 drafts × 2 tasks/call = 10–30 tasks/month. Headroom ~3×.
- Per-brand cost at Free tier: $0.
- Escalation: Starter plan is $19.99/mo for 750 tasks. Even if all 4 brands scale to Quill's higher cadence (10 drafts/day × 30 days × 2 tasks = 600 tasks/mo per brand), Starter covers each brand for ~$20/mo. 3-yr TCO across 4 brands ≈ $960 worst case.

## Related

- Parent plan: [`~/.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md`](../../.claude/plans/2026-05-20-phases-4-7-through-4-10-detail.md)
- Existing email-triage (read-only, hard refuses send): [`hermes/shared-skills/email-triage/account_registry.py`](../../hermes/shared-skills/email-triage/account_registry.py)
- Marin profile config (target for pilot wiring): [`hermes/profiles/marin/config.yaml`](../../hermes/profiles/marin/config.yaml)
- Brand-credential-isolation memory: `~/.claude/projects/-Users-alexhale-Projects-agents/memory/feedback_brand_credential_isolation.md`
- Magica docs (rejected primitive, reference for separate content-pipeline evaluation): https://magica.com/docs/introduction/overview
- Zapier MCP product page: https://zapier.com/mcp
- Zapier data retention: https://zapier.com/legal/data-retention-deletion
