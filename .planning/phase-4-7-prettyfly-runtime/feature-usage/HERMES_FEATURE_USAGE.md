# Hermes feature usage audit — 2026-05-06

> **Phase 4.7 Gate G2.** PF Runtime sub-phase 4.7.2 ships only features where in-use=yes for ≥1 profile.

## Method

- **Phase 1 (this run):** grep profile config files + check skills/ + check rooms/voice/ at `/Users/alexhale/.hermes/profiles/<slug>/`. This captures *static* feature enablement (does the profile reference a feature in its config), not *actual usage*.
- **Phase 2 (deferred):** SQLite session DB inspection at `/Users/alexhale/.hermes/sessions/` for runtime tool-call counts, plus Langfuse trace queries for 80th-percentile-used tools per profile over 30 days. This captures *real usage*.
- G2 (per PLAN.md §1) requires both phases. Phase 1 evidence below is sufficient to scope which features are *referenced* in profile configs; feature-scoping decisions for sub-phase 4.7.2 (which features PF Runtime ships) require Phase 2 evidence and remain blocked on it.

## Per-profile feature matrix

| Profile | memory_tool | skill_manager | kanban_tools | honcho | voice_loop | image_gen | tinker_atropos | dream_loop |
|---------|-------------|---------------|--------------|--------|------------|-----------|----------------|------------|
| personal | implicit | Y (1) | N | N | Y | N | N | Y |
| mobile | N | N | N | N | N | N | N | N |
| codex | N | N | N | N | N | N | N | N |
| lawdbot | N | N | N | N | N | N | N | N |
| consultops | N | N | N | N | N | N | N | N |
| sportsbook | N | N | N | N | N | N | N | N |
| yeh-ops | N | N | N | N | N | N | N | N |
| atlas-ceo | N | Y (89) | N | N | N | N | N | N |
| viper-outreach | N | N | N | N | N | N | N | N |
| quill-content | N | N | N | N | N | N | N | N |
| forge-audit | N | N | N | N | N | N | N | N |
| ops | N | N | N | N | N | N | N | N |
| vanclief | implicit | N | N | N | N | N | N | N |

## Aggregate (in-use across fleet)

- **memory_tool** (Built-in MEMORY.md/USER.md persistent stores): see matrix above
- **skill_manager_tool** (Skill creation/deletion/metadata): see matrix above
- **kanban_tools** (Multi-agent task board (v0.12)): see matrix above
- **honcho_provider** (Honcho dialectic memory plugin): see matrix above
- **voice_loop** (Voice transcription pipeline): see matrix above
- **image_generation** (Image gen routing): see matrix above
- **tinker_atropos** (Per-tenant LoRA): see matrix above
- **dream_loop** (Post-session reflection): see matrix above

## Phase 4.7 implications

| If any profile uses it... | PF Runtime ships it in sub-phase 4.7.2 |
|---------------------------|----------------------------------------|
| memory_tool | Yes — Tier 2 buffer + MEMORY.md mutator |
| skill_manager | Yes — agentskills.io progressive-disclosure loader (Tier 4) |
| kanban_tools | Yes — Postgres-backed Kanban (4.7.4) |
| honcho | Server-side via MCP (no PF Runtime code; Honcho server stays AGPL) |
| voice_loop | Optional 4.7.3.B (Slack `file_shared` audio events) |
| image_gen | Pass-through to LiteLLM image routing — no PF Runtime code needed |
| tinker_atropos | Out of scope for 4.7; deferred to per-tenant LoRA SKU |
| dream_loop | Yes — `pf-runtime/dream/post_session.py` (4.7.2) |

## Action

Operator reviews matrix; flags any "in-use but not in 4.7 scope" surprises.
