# changelog — sentinel

## 2026-05-30 — Profile scaffolded from Quill template

Initial profile. Built per the 11-file contract ADR
(`_meta/decisions/2026-05-18-agent-shape-11-file-contract.md`). Steals the
Polsia SEO/AEO task catalog (`docs/competitive-intel/polsia/03-seo-aeo-social-task-playbook.md`)
and adapts the Sentinel v1 posture patterns from `yehovah/seo-agent/soul.js`.

- **Identity**: SOUL / DOCTRINE / USER / MEMORY written against prettyflyforai.com
  audit gaps (missing title/meta/OG, HIGH risk per Polsia audit 2026-05-30)
- **Doctrine**: VERIFY-THEN-DEPLOY gate, AEO = normal SEO + structure rule,
  source anchors (Google Search Central + arXiv 2605.14021 / 2604.27790 /
  2603.29979), banned tactics (llms.txt as primary, magic schema, auto-deploy)
- **User**: prettyflyforai.com positioning lock ("Workflow-First AI Operations &
  Systems Advisory for service businesses"), ICP (technical B2B CEO, 10-50
  employee SaaS)
- **Memory**: current audit gap queue (title/meta/OG/OrgSchema all MISSING),
  Sentinel v1 prior-art path, Marin/Sentinel/Quill/Stet boundary and handoff chain
- **Router**: CLAUDE.md with 7-task routing + 3-tier model routing (nvidia free /
  sonnet-4-6 / opus-4-7) + 11 hard rules
- **Skills**: 6 flat skill stubs (aeo-technical-audit, generate-metadata-schema-pack,
  aeo-question-cluster-brief, competitor-citation-teardown, opportunity-score,
  self-audit) — content owned by other agents, directories scaffolded with .gitkeep
- **Manifests**: manifest.json + a2a-card.json adapted from Quill (sku/agent_id
  "sentinel", department "marketing", tier "seo_aeo_execution_pilot",
  side_effects read+proposal_write_only, 6 sentinel skills + 3 shared agency skills,
  cost budget $5/day)
- **Acceptance gate**: ONE measurable — first real artifact + matching
  sentinel.draft.proposed receipt, falsifiable in 1 local receipt check
- **Boundary established**: Marin (strategy) → Sentinel (execution artifacts) →
  Quill (copy) → Stet (critique) is the handoff chain

Lint: scaffold-only (PASS expected on soft mode).
Skills: directories with .gitkeep only — real SKILL.md files to be added when
each skill is built and gate-cleared.
