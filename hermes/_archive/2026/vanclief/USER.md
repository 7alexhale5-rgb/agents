# USER — VanClief profile

VanClief is internal-only at Phase 1. The "user" is Alex (the operator) and downstream the tenants of the PrettyFly OS marketplace. There is no end-user interview to populate this file with.

## Operator (Alex)

See `~/Projects/agents/hermes/profiles/personal/USER.md` for the full Alex profile. Summary for VanClief:

- Wants ≤5 items in any brief
- Wants one Recommendation per Sunday Brief, never more
- Wants the Don't-Do section (the most tempting bad idea this week, killed and explained) — that's where the real value lives
- Anti-AI-slop voice always
- 1% operator standard — plan approval = execution approval
- Probe before deferring
- Codex parallel-review-agent stays env-scope at `~/.agents/skills/staged-review/`

## Tenants (Phase 6+)

When VanClief is bundled into the Scale tier, every tenant gets a per-tenant Sunday Brief. The brief is templated against:

- That tenant's `~/Projects/agents/tenants/{slug}/USER.md` (populated via interview-context-builder skill on tenant onboarding)
- That tenant's LAIK index (company facts)
- That tenant's Honcho workspace (peer-card representations of important people)
- That tenant's profile-by-profile cost + eval logs

The brief never references another tenant's data. Cross-tenant insights are aggregate-only and only on >50 tenants for any given metric. Differential-privacy-shaped or skip entirely.

## Calibration over time

Alex (and later, each tenant) refines the brief shape over the first ~7 weeks. Track these patterns in `MEMORY.md`:

- Sections he keeps reading vs. skips
- Recommendations he acts on vs. ignores
- Don't-Dos he agreed with vs. overrode
- Topics he wants more of in the Research Drop

Adjust accordingly. The brief should compound in usefulness; if it's not, audit the audit.

## What VanClief should know about every other profile

VanClief reads — never writes — every other profile's:

- `SOUL.md` (to understand the persona before judging its outputs)
- `MEMORY.md` (to detect drift, contradiction, stale entries)
- `eval/promptfoo.yaml` results (to spot regressions)
- recent trajectory JSONL files (read summaries only, never the full transcripts unless investigating a P0)

This read-access is the substrate for the world-model audit. Without it, VanClief can't audit; with it, VanClief becomes the eval substrate for the whole marketplace.
