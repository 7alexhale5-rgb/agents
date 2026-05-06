# Memory lifecycle — 4-tier read/write semantics

> **Status:** locked 2026-05-06 per architecture-finding-1 in Phase 4.7 PLAN.md §6.B. PF Runtime sub-phase 4.7.2 builds against this contract.

## The four tiers

| Tier         | Source                                                          | Mutability                                     | Latency                | Concurrency                           |
| ------------ | --------------------------------------------------------------- | ---------------------------------------------- | ---------------------- | ------------------------------------- |
| 1 — SOUL     | `hermes/profiles/{slug}/{SOUL,USER,CLAUDE}.md`                  | Read-only at runtime; edited via human commits | <1ms (mtime-cached)    | Unbounded readers                     |
| 2 — Buffer   | `pf-runtime/runtime-state/{slug}/buffer.sqlite`                 | Append-only with 30-day TTL eviction           | <10ms write, <2ms read | SQLite WAL, single writer per profile |
| 3 — Episodic | LAIK MCP (`laik_query`) over per-tenant pgvector                | Async batch write every 30s                    | <100ms p95 read        | Bounded by LAIK MCP rate limit        |
| 4 — Skills   | `hermes/profiles/{slug}/skills/` + `~/.hermes/skills/` (shared) | Skill-gen synchronous after operator approval  | <5ms                   | Lockfile during write                 |

## Read-through ordering

Read returns the first non-empty match in this fall-through:

```
read(profile_slug, session_id) → Messages =
    tier1_soul(profile_slug)              # always returns SOUL/USER/CLAUDE/MEMORY content
    ⊕ tier2_buffer(profile_slug, session_id)  # last-N session messages
    ⊕ tier3_episodic(profile_slug, query)     # LAIK MCP semantic recall (top-k=8)
    ⊕ tier4_skills(profile_slug, context)     # skill descriptions matching context

# ⊕ = ordered concatenation, deduplicated by content hash
```

The read-through is cache-aware: tier 1 has 30s mtime cache; tier 2 has no cache (SQLite is fast enough); tier 3 has 60s session cache; tier 4 has 5min skill-list cache invalidated on skill_gen write.

## Write barriers

| Tier       | Write mode                                                                                                       | Visibility                                                                           |
| ---------- | ---------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| 1 SOUL     | Read-only at runtime                                                                                             | Edits land via `git commit` + `sync-profile.sh push`; runtime reload on mtime change |
| 2 Buffer   | Synchronous, blocks caller                                                                                       | Visible to next read in <10ms                                                        |
| 3 Episodic | Async batch (queued, flushed every 30s OR on session end)                                                        | Visible after batch flush                                                            |
| 4 Skills   | Synchronous after operator approval (or autonomous on `personal` profile only per `manifest.skill_gen_autonomy`) | Visible to next session                                                              |

**Concurrency invariant:** during dream-loop compaction, tier 2 buffer is read-only for that profile. New writes to tier 2 are queued in a per-profile asyncio.Queue and applied after compaction completes. Compaction lasts <30s under normal load; the queue is unbounded but bound-checked by `BoundsAuditor` (max 100 queued messages → halt + alert).

## Dream-loop merge semantics

The dream loop runs post-session, async, idempotent. Algorithm:

```python
async def post_session_compaction(profile_slug: str, session_id: str):
    # Idempotency: skip if already compacted for this session
    if await audit.dream_compaction_exists(profile_slug, session_id):
        return

    # Take read lock on tier 2 for this profile
    async with buffer_compaction_lock(profile_slug):
        # Read last 24h of tier 2 + tier 3 for this profile
        recent_buffer = await tier2.read_window(profile_slug, hours=24)
        recent_episodic = await tier3.read_window(profile_slug, hours=24)

        # Prompt LLM (tier-cheap per ADR-005) for compaction diff
        diff = await llm.complete(
            system=DREAM_LOOP_SYSTEM_PROMPT,
            messages=[
                Message("user", json.dumps({
                    "current_memory_md": current_memory,
                    "recent_buffer": recent_buffer,
                    "recent_episodic": recent_episodic
                }))
            ]
        )

        # Safety: large-diff threshold
        if diff.lines_deleted / max(1, current_memory.lines) > 0.50:
            # Operator-approval-required for any profile
            await alert_forge_audit(profile_slug, session_id, diff)
            return

        # Apply diff
        if profile_slug == "personal" or operator_approved(diff):
            await apply_diff_to_memory_md(profile_slug, diff)
            await audit.record_dream_compaction(profile_slug, session_id, diff)
        else:
            await queue_for_operator_review(profile_slug, diff)
```

**Contradiction flagging:** dream loop emits a `contradictions: [...]` array in the diff metadata. Each contradiction names the conflicting line numbers and the temporal evidence (`"buffer line 42 contradicts memory line 18; buffer is more recent"`). Operator reviews contradictions in `forge-audit` profile before applying.

## Failure modes

| Failure                                | Behavior                                                                                  |
| -------------------------------------- | ----------------------------------------------------------------------------------------- |
| Tier 1 SOUL.md missing                 | Runtime refuses to start profile; profile-dir contract test catches this nightly          |
| Tier 2 SQLite locked                   | Retry with exponential backoff up to 5 attempts; surface `MemoryUnavailable` after        |
| Tier 3 LAIK MCP unavailable            | Fall back to local SQLite cache for last 24h; alert `forge-audit`; resume on MCP recovery |
| Tier 4 skill load error                | Skip the broken skill; alert `forge-audit`; runtime continues                             |
| Dream loop large-diff threshold breach | Halt; queue for operator review; alert `forge-audit`                                      |

## Test gates (sub-phase 4.7.2)

- `tests/memory_consistency_test.py` — 100-message corpus + concurrent skill-gen + dream-loop on `personal` profile. Assert: zero lost writes, read-after-write sees latest, post-compaction tier 2 + tier 3 view consistent.
- 24h soak: ≥1 dream-loop firing with non-empty diff, contradiction flagging works on synthetic test data, zero large-diff threshold breaches.
- Ragas faithfulness ≥ Hermes baseline – 0.02 on 30-question golden set.
