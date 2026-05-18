# agents — Backlog

Staged work for the Hermes monorepo. Items here originate from CI ingest or ad-hoc capture. Format per `~/.carl/ci_ingest` CI_INGEST_RULE_2.

---

## Hermes/Pantheon competitor audit — ratify decision + surface to atlas-ceo — INTEGRATE

- **CI source**: `~/Projects/memory-vault/continuous-improvement/2026-05-15-hermes-pantheon-competitor-audit.md`
- **Verdict + reason**: INTEGRATE — the 2026-05-16 decision draft already exists at `~/Projects/memory-vault/decisions/2026-05-16-hermes-pantheon-audit.md` (status: `draft, awaiting Alex review`); this entry is to ratify it and propagate findings into atlas-ceo's reading context.
- **What to do**:
  1. Re-read `~/Projects/memory-vault/decisions/2026-05-16-hermes-pantheon-audit.md` end-to-end. Confirm or revise the 3 PFOS advantages + 3 borrowable Hermes patterns comparison table.
  2. Flip frontmatter `status: draft (research output, awaiting Alex review)` → `status: ratified YYYY-MM-DD`. Append a `## Ratification` block summarizing the user's decision.
  3. Create `~/Projects/agents/hermes/profiles/atlas-ceo/memory/competitive-intel.md` (≤30 lines, no exposition) — the 3-pattern + 3-advantages summary, bidirectionally linked to the decision doc.
  4. If any Hermes patterns are worth borrowing, queue a `/design-stack` ticket via a follow-up note in the atlas-ceo `BUSINESS.md` or `manifest.json`.
- **Effort estimate**: 30 min
- **Acceptance criterion**: decision frontmatter shows `status: ratified`; `~/Projects/agents/hermes/profiles/atlas-ceo/memory/competitive-intel.md` exists with the comparison table; bidirectional link verified.
