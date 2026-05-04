# Honcho — operations runbook

## What it is

Honcho is the dialectic memory backend that powers per-tenant peer cards across Hermes profiles. Three reasoning agents:

- **Deriver** — extracts observations from messages, builds peer representations
- **Dialectic** — answers questions about peers by gathering memory context
- **Dream** — consolidates observations overnight into long-term insights

## License — read this before deploying

**AGPL-3.0.** That means: if you ship Honcho's source code (or a derivative) to a third party, you must release your modifications under AGPL. **Per ADR-001 hard constraint #5: Honcho stays server-side, network-attached only.** Never bundle into a tenant deliverable.

The on-prem Scale tier ($9,999/mo) ships Honcho only with a commercial Honcho license (purchase from plastic-labs).

## Phase 1.5 — laptop self-host

```bash
cd ~/Projects/agents/honcho
cp .env.template .env
# Generate secrets
openssl rand -hex 32  # use this for HONCHO_DB_PASSWORD
openssl rand -hex 32  # use this for HONCHO_JWT_SECRET
# Edit .env, paste secrets, paste model keys (Anthropic + OpenAI minimum)

docker compose up -d
docker compose logs -f honcho-api  # wait for "Application startup complete"

# Smoke test
curl -fsS http://localhost:8765/health
# Expected: 200 OK with health JSON

# Probe the API
curl -fsS http://localhost:8765/v1/workspaces \
  -H "Authorization: Bearer $(python3 -c 'import jwt; print(jwt.encode({"sub":"system"},"YOUR_JWT_SECRET",algorithm="HS256"))')"
```

## Wiring into a Hermes profile

In `~/.hermes/profiles/<name>/config.yaml`:

```yaml
memory:
  honcho:
    enabled: true
    url: http://localhost:8765
    workspace: <profile-name>
    auth_token_env: HONCHO_JWT_TOKEN_<PROFILE>
```

Generate a profile-scoped JWT and store in profile's `.env`. Hermes will attach Honcho as a memory provider on next start.

## Phase 4 — prod (VPS sibling Postgres)

Move to `167.71.113.40:8766` (sibling to Langfuse Postgres on 5432). Same docker-compose; bind to localhost on a different port so Caddy never exposes it. Tenant traffic to Honcho goes through Hermes runtime, never tenant → Honcho directly.

## Backup

Honcho's pgvector volume contains tenant-scoped peer cards + sessions. Daily backup:

```bash
docker exec honcho-db pg_dump -U honcho honcho | gzip > \
  ~/Projects/_archive/2026/honcho-backups/$(date +%Y%m%d).sql.gz
```

Restore:

```bash
gunzip -c backup.sql.gz | docker exec -i honcho-db psql -U honcho honcho
```

## Common issues

### `honcho-api` health check fails

Check `docker compose logs honcho-api`. Most common: `LLM_ANTHROPIC_API_KEY` missing (the Deriver agent fails to start). Fix the env, `docker compose up -d`.

### Deriver lag

If conversations land in Honcho but peer cards don't update for hours, the Deriver worker may be backlogged. `docker compose logs honcho-deriver` will show it. Scale by adding more deriver replicas in compose if volume warrants.

### Cross-tenant leak (catastrophic)

If a Hermes profile's `peer.search()` returns rows tagged with another tenant's `workspace_id`, **halt all profiles immediately** (`scripts/seal-profile.sh <each>`), audit the JWT scoping, file a P0 incident. Honcho's workspace isolation is enforced at the SQL level — a leak means the JWT scoping is broken.

## Kill switch

```bash
docker compose stop  # halts all 3 containers, data persists
docker compose down  # halts + removes containers, data persists in named volume
docker compose down -v  # halts + removes containers AND data — only use for clean reset
```
