# LAIK MCP — runtime-agnostic boundary spec

> **Status:** **DRAFT pending Phase 4.5 lead sign-off.** Authored 2026-05-06 per Phase 4.7 PLAN.md §14.A. Phase 4.5 ships against this contract; PF Runtime consumes it identically to Hermes. The "locked" stamp moves here only after the Phase 4.5 lead has reviewed the surface in-context, signed off in commit-message form, and the contract test (`tests/laik_mcp_contract.py`) is green against the actual Phase 4.5 implementation.

## Purpose

LAIK (`~/Projects/local-ai-kit`) provides per-tenant grounded retrieval (hybrid RAG + read-only SQL + propose-not-execute mutations + Ragas eval). This MCP server exposes it as a tool surface that any MCP-aware runtime — Hermes today, PF Runtime tomorrow — can attach to a profile via standard `mcp.yaml`. The MCP boundary is intentionally **runtime-agnostic**: zero Hermes-specific extensions, zero PF Runtime-specific extensions.

## Six tools

### 1. `laik_status`

Returns service health + tenant count + index sizes.

```json
{
  "input": {},
  "output": {
    "ok": "boolean",
    "tenants": "number",
    "total_chunks": "number",
    "ragas_floor": "number"
  }
}
```

### 2. `laik_list_tenants`

Lists tenants visible to the calling profile (RBAC-gated).

```json
{
  "input": { "profile_slug": "string" },
  "output": {
    "tenants": [
      {
        "slug": "string",
        "display_name": "string",
        "ingested_gb": "number",
        "last_ragas": "number"
      }
    ]
  }
}
```

### 3. `laik_query`

Hybrid RAG retrieval over a tenant's grounded knowledge base.

```json
{
  "input": {
    "caller_profile_slug": "string (required) — the agent profile making the call; bound to session_token at MCP attach time",
    "session_token": "string (required) — JWS signed at MCP attach by runtime; payload {profile_slug, session_id, tenant, exp}; verified against laik's runtime pubkey",
    "tenant": "string",
    "query": "string",
    "top_k": "number (default 8, max 30)",
    "filters": { "doc_type": "string?", "since": "ISO8601?" }
  },
  "output": {
    "chunks": [
      {
        "id": "string",
        "content": "string",
        "score": "number",
        "source_uri": "string",
        "frontmatter": "object"
      }
    ],
    "trace_url": "string (Langfuse)",
    "ragas_faithfulness": "number"
  }
}
```

### 4. `laik_sql`

Read-only SQL against a tenant's allowlisted tables (executed under `mcp_readonly` Postgres role).

```json
{
  "input": {
    "caller_profile_slug": "string (required)",
    "session_token": "string (required) — see §3 schema",
    "tenant": "string",
    "sql": "string",
    "params": "array?"
  },
  "output": {
    "rows": "array",
    "columns": "array",
    "row_count": "number",
    "ms": "number"
  }
}
```

**Hard constraints:** SELECT-only at the role level; statement timeout 5000ms; max 1000 rows; blast-radius detector rejects table-scans on tables >100K rows without LIMIT.

### 5. `laik_propose_mutation`

Stages a write proposal in `mutation_proposals` table; **never executes**.

```json
{
  "input": {
    "caller_profile_slug": "string (required)",
    "session_token": "string (required) — see §3 schema",
    "tenant": "string",
    "operation": "INSERT | UPDATE | DELETE",
    "table": "string",
    "rows_affected": "array (preview)",
    "rationale": "string",
    "session_id": "string"
  },
  "output": {
    "proposal_id": "uuid",
    "diff_url": "string (admin UI)",
    "status": "pending"
  }
}
```

### 6. `laik_confirm_mutation`

Confirms a previously staged proposal. Operator approval is encoded as a **signed approval token** — never a raw `confirmer_user_id` string (which would be agent-forgeable). The admin UI mints the token after operator tap; LAIK verifies the JWS against the admin-UI public key before applying.

```json
{
  "input": {
    "caller_profile_slug": "string (required) — must match the profile that originally proposed",
    "session_token": "string (required) — see §3 schema",
    "approval_token": "string (required) — JWS signed by admin UI; payload {proposal_id, confirmer_user_id, tenant, exp (≤300s after issuance), nonce}; verified server-side against admin_ui pubkey before any mutation runs"
  },
  "output": {
    "status": "applied | rejected",
    "audit_id": "uuid",
    "rows_committed": "number"
  }
}
```

**Replay protection:** `approval_token.nonce` is recorded in `mutation_audit.approval_nonce` with a UNIQUE constraint; replays reject with `LAIK_APPROVAL_REPLAYED`.

### Tenant-scoped tool security (applies to §3–§6)

All tenant-scoped tools require both `caller_profile_slug` and `session_token`. The MCP server:

1. Verifies `session_token` JWS signature against the runtime's pubkey (rotated per session).
2. Asserts `session_token.payload.profile_slug == caller_profile_slug` (defends against agents forging the slug header).
3. Asserts `session_token.payload.tenant == tenant` (input arg) — the explicit `tenant` input MUST equal the signed `tenant` claim. Mismatch is an attempt to bypass RLS scoping.
4. Asserts `caller_profile_slug` is in the tenant's RBAC allowlist for the requested operation.
5. Asserts `session_token.exp > now()` (default TTL 1h).
6. Sets `SET LOCAL laik.session_tenant = session_token.payload.tenant` on the Postgres session before any query (drives the RLS policy in §Multi-tenant isolation).

Failure of any check returns `LAIK_SESSION_INVALID` and audits the attempt to `laik_audit.session_violations`.

## Error contract

All tools emit MCP-standard `{ "error": { "code": string, "message": string, "data": object? } }`. Codes:

- `LAIK_TENANT_NOT_FOUND` — 404-equivalent; profile lacks RBAC for that tenant
- `LAIK_RAGAS_BELOW_FLOOR` — query returned but faithfulness <0.85; chunks still returned for inspection
- `LAIK_SQL_FORBIDDEN` — non-SELECT or table not on allowlist
- `LAIK_PROPOSAL_DUPLICATE` — proposal hash matches an unconfirmed pending one
- `LAIK_RATE_LIMITED` — per-profile cap exceeded (configured per tier)
- `LAIK_SESSION_INVALID` — `session_token` missing, expired, signature invalid, or `profile_slug` mismatch with `caller_profile_slug`
- `LAIK_APPROVAL_REPLAYED` — `approval_token.nonce` already recorded in `mutation_audit`
- `LAIK_APPROVAL_INVALID` — `approval_token` missing, expired (>300s after issuance), or signature invalid against admin_ui pubkey

## Versioning

- Tool schemas live in `mcp-servers/laik/server.py` `@tool` decorators with `version: "1.0"`.
- Breaking changes ship as a parallel `laik_v2_*` tool surface; old tools deprecate after 90 days.
- Profile `mcp.yaml` entry pins version: `laik: { version: "1.0", url: "stdio:..." }`.

## Multi-tenant isolation (RLS)

`mutation_proposals`, `mutation_audit`, and any per-tenant LAIK table MUST enable Postgres Row-Level Security with `tenant_id` as the discriminator. RLS policy:

```sql
ALTER TABLE laik.mutation_proposals ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON laik.mutation_proposals
  USING (tenant_id = current_setting('laik.session_tenant', true)::uuid)
  WITH CHECK (tenant_id = current_setting('laik.session_tenant', true)::uuid);
```

The MCP server sets `laik.session_tenant` in the Postgres session via `SET LOCAL` from the verified `session_token.payload.tenant` BEFORE any query runs. The `mcp_readonly` and `mcp_writer` roles are non-bypass-RLS (`NOBYPASSRLS`). A defense-in-depth invariant: even if the MCP server accidentally reuses a connection across tenants, RLS prevents cross-tenant reads/writes.

## Test surface

- `mcp-servers/laik/smoke.py` — calls all 6 tools against a synthetic tenant, asserts shapes match this SPEC.
- `tests/laik_mcp_contract.py` (new for Phase 4.7) — contract test that any runtime (Hermes or PF Runtime) can attach to and exercise the surface without runtime-specific shims. **Cross-tenant assertions:**
  - With `caller_profile_slug=X` + `tenant=A`, attempt `laik_sql` reading `mutation_proposals.tenant_id=B` → MUST return zero rows (RLS isolation).
  - Mismatched `session_token.profile_slug != caller_profile_slug` → MUST return `LAIK_SESSION_INVALID`.
  - Replay of `approval_token.nonce` already in `mutation_audit` → MUST return `LAIK_APPROVAL_REPLAYED`.
  - Expired `session_token.exp` → MUST return `LAIK_SESSION_INVALID`.

## Consumption pattern (any runtime)

```python
# PF Runtime example — identical to Hermes' MCP attachment
from mcp_client import MCPClient
client = MCPClient.attach("laik", config_path="~/Projects/agents/hermes/profiles/<slug>/mcp.yaml")
result = await client.call("laik_query", { "tenant": "consultops", "query": "...", "top_k": 8 })
```

No Hermes-specific imports, no PF Runtime-specific imports. The MCP standard is the entire interface.

## Ownership

Phase 4.5 (LAIK-as-MCP fusion) ships against this spec. Phase 4.7 (PF Runtime) consumes it. Cross-repo grant boundary per LAIK ADR-0001 stays intact: LAIK owns its own schema; consuming runtimes own their own schemas; the MCP interface is the shared boundary.
