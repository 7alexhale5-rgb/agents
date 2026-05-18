# Skill self-generation bounds — runaway safeguards

> **Status:** locked 2026-05-06 per architecture-finding-4 in Phase 4.7 PLAN.md §6.C. Enforced by `pf-runtime/dream/bounds_audit.py`.

## The four hard caps

| #   | Bound                                | Default                              | Configurable per profile?                                           |
| --- | ------------------------------------ | ------------------------------------ | ------------------------------------------------------------------- |
| 1   | Max new skills per 72h               | **3**                                | Yes — `manifest.skill_gen.max_new_per_72h`                          |
| 2   | Max skill markdown LOC               | **100**                              | Yes — `manifest.skill_gen.max_markdown_loc` (excluding code blocks) |
| 2b  | Max skill code-block LOC             | **300**                              | Yes — `manifest.skill_gen.max_code_loc`                             |
| 3   | Cost ceiling per profile per day     | **10% of LiteLLM tier daily budget** | Yes — `manifest.skill_gen.cost_pct_of_daily_budget`                 |
| 4   | Max episodic skill mutations per day | **50**                               | Yes — `manifest.skill_gen.max_episodic_writes`                      |

Defaults come from VanClief's audit observations on similar self-modifying systems plus the `~/Projects/music/` 2-week-sandbox precedent.

## Trigger logic

Skill self-gen fires when:

1. A session completes with **≥5 tool calls**, AND
2. The session's tool-call sequence is novel (Levenshtein distance >0.5 vs nearest existing skill), AND
3. The profile's `manifest.skill_gen_autonomy` is `auto` or (`approve` and operator approves the proposal), AND
4. None of bounds 1-4 are at or over cap

If any condition fails, the candidate skill is dropped silently (no operator alert — too noisy).

## Bound check flow

```python
# pf-runtime/dream/bounds_audit.py

class BoundsAuditor:
    async def check_and_record(self, profile_slug: str, candidate_skill: SkillProposal) -> AuditResult:
        # Check all four bounds
        new_in_72h = await self.count_new_skills_72h(profile_slug)
        if new_in_72h >= self.cap_new_per_72h(profile_slug):
            await self.alert_forge_audit(profile_slug, "max_new_per_72h", new_in_72h)
            return AuditResult.HALT_PROFILE

        if candidate_skill.markdown_loc > self.cap_markdown_loc(profile_slug):
            return AuditResult.REJECT_TOO_LARGE

        if candidate_skill.code_loc > self.cap_code_loc(profile_slug):
            return AuditResult.REJECT_TOO_LARGE

        cost_today = await self.skill_gen_cost_today(profile_slug)
        budget_today = await self.tier_budget_today(profile_slug)
        if cost_today / budget_today > self.cap_cost_pct(profile_slug):
            await self.alert_forge_audit(profile_slug, "cost_ceiling", cost_today)
            return AuditResult.HALT_PROFILE_FOR_TODAY

        episodic_today = await self.episodic_writes_today(profile_slug)
        if episodic_today >= self.cap_episodic_writes(profile_slug):
            await self.alert_forge_audit(profile_slug, "max_episodic_writes", episodic_today)
            return AuditResult.HALT_PROFILE_FOR_TODAY

        return AuditResult.APPROVED
```

## Halt semantics

- `HALT_PROFILE` — skill_gen disabled for this profile until operator manually re-enables via `pf-runtime skill-gen enable --profile <slug>`. Profile continues running normally for everything except skill_gen.
- `HALT_PROFILE_FOR_TODAY` — skill_gen disabled until midnight ET; auto-resumes.
- `REJECT_TOO_LARGE` — silent reject, candidate dropped, no operator alert.

## Alerting

All halts emit a `forge-audit` Slack message + Langfuse trace tag `pf_runtime.skill_gen.halt` + Sentry event with `severity=warning`. Three or more halts in 24 hours across the fleet escalates to `severity=error` (operator pages).

## Test gates (sub-phase 4.7.2 24h soak)

- Synthetic rate-limit-bypass attempt: 10 candidate skills proposed in 1 hour; assert ≤3 admitted, ≥7 halted with correct reason codes.
- Cost-cap test: skill_gen invocations driven to 11% of daily budget; assert HALT_PROFILE_FOR_TODAY fires exactly at 10%.
- Large-skill rejection: candidate with 200 markdown LOC; assert REJECT_TOO_LARGE without operator alert.

## Per-profile overrides (allowed)

Profiles with stricter trust posture (e.g., `vanclief` audit profile, money-pipeline profiles) can lower the caps via `manifest.skill_gen`:

```yaml
# hermes/profiles/sportsbook/manifest.json (example)
{ "skill_gen": { "max_new_per_72h": 1, ? // stricter than default 3
        "max_markdown_loc"
      : 60, ? // stricter than default 100
        "cost_pct_of_daily_budget"
      : 0.05, ? // half default
        "max_episodic_writes"
      : 20        // half default } }
```

Profiles cannot raise caps above the defaults via per-profile config; that requires editing this document + Codex review.

## Code-block quarantine (added 2026-05-06 post-swarm review)

**Rule.** Auto-authored skills are restricted to **frontmatter + markdown body only**. Any fenced code block (` ``` `), indented code block (4-space lead), or HTML `<code>` block in the candidate body triggers operator approval regardless of the profile's `manifest.skill_gen_autonomy` setting.

**Why.** A poisoned inbound message can convince the system that a useful skill is missing. Without this rule, the `personal` profile's `skill_gen_autonomy: auto` would auto-write a skill containing arbitrary code into `~/.hermes/skills/{slug}/` (or `hermes/profiles/{slug}/skills/`) — that's a remote-code-write primitive on the operator's machine.

**Enforcement.** `BoundsAuditor.check_and_record` runs a regex pass over the candidate body BEFORE bound checks 1–4. If `code_block_count > 0`, the result is `PENDING_OPERATOR_REVIEW` regardless of profile. Operator-approved code-bearing skills land normally; auto-rejected ones do NOT count toward the 3-per-72h cap (otherwise an attacker can drain the budget with junk to block legitimate self-gen).

**What counts as a code block.** The detector matches: triple-backtick fences (with or without language hint), indented blocks of ≥3 consecutive lines starting with 4+ spaces, HTML `<code>` and `<pre>` tags, and shell-prompt-prefixed lines (`$ ...`). Frontmatter YAML is exempt — its parser treats every value as data, never as code.

**What this rule does NOT block.** The skill markdown body can still describe code patterns in prose ("call the X function with Y args"), and can reference external scripts by path. What it blocks is candidate skills that ship executable code inline.

**Trace surface.** Mutation audit records `code_block_count` and a sha256 of the candidate body. The body itself is not stored — preventing mutation-audit-from-becoming-a-secret-store. THREAT_MODEL.md A4 names this as the canonical defense for skill-self-gen poisoning.

**Test gate.** `tests/skill_gen_quarantine_test.py` — fixtures: (a) markdown-only candidate (passes), (b) candidate with one fenced code block (operator review required), (c) candidate with indented code block (operator review required), (d) attacker fixture using HTML `<pre>` to evade fence detection (operator review required), (e) frontmatter with multiline string value that LOOKS like code (passes — frontmatter is data).

## Reversibility

Bound config changes are TYPE-2 reversible (config edits, no schema). Skill registry rollback is via git: `cd hermes/profiles/<slug>/skills && git revert HEAD`.
