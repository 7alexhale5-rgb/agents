# Hermes Skill Arsenal Map

Source snapshot: `msitarzewski/agency-agents` `783f6a7`.

This is the ownership view for the current skill arsenal. It covers profile-local Hermes skills, shared Hermes skills, platform scaffolding skills, and the Agency-derived shared skills.

## Visual Fit Map

```mermaid
flowchart TB
  agency["Agency catalog\n184 addressed"] --> shared["Hermes shared skills\n64 converted now"]
  native["Existing Hermes skills\nprofile + shared + platform"] --> arsenal["Skill arsenal"]
  shared --> arsenal
  arsenal --> atlas["Atlas CEO\nexecutive decisions"]
  arsenal --> marin["Marin\nrevenue + marketing"]
  arsenal --> quill["Quill\ndrafting + creative"]
  arsenal --> stet["Stet\ncritique + evidence"]
  arsenal -. parked .-> techop["Future technical-operator\nengineering governance"]
```

## Active Arsenal Counts

| Source | Count |
| --- | ---: |
| agency-shared | 64 |
| platform | 1 |
| profile-local | 24 |
| shared | 2 |

| Owner | Count |
| --- | ---: |
| All profiles | 1 |
| Atlas CEO | 13 |
| Atlas CEO, Marin | 1 |
| Atlas CEO, Stet | 1 |
| Fleet builder | 1 |
| Koho/Yeh future retainer profiles | 1 |
| Marin | 17 |
| Marin, Quill | 1 |
| Parked for future technical-operator | 19 |
| Parked until artifact trigger | 5 |
| Parked until channel/tool trigger | 10 |
| Quill | 9 |
| Quill, Stet | 1 |
| Stet | 11 |

## Every Active Skill

| Skill | Owner | Source | Kind | Fit | Status | Path |
| --- | --- | --- | --- | --- | --- | --- |
| `finance-tax-strategist` | Atlas CEO | agency-shared | Agency-derived shared skill | Advisory/readiness skill with current-source gates and human review. | converted-curated | `hermes/shared-skills/agency/finance-tax-strategist/SKILL.md` |
| `product-behavioral-nudge-engine` | Atlas CEO | agency-shared | Agency-derived shared skill | Owned by Atlas CEO for executive decision support | converted | `hermes/shared-skills/agency/product-behavioral-nudge-engine/SKILL.md` |
| `product-feedback-synthesizer` | Atlas CEO | agency-shared | Agency-derived shared skill | Owned by Atlas CEO for executive decision support | converted | `hermes/shared-skills/agency/product-feedback-synthesizer/SKILL.md` |
| `product-manager` | Atlas CEO | agency-shared | Agency-derived shared skill | Owned by Atlas CEO for executive decision support | converted | `hermes/shared-skills/agency/product-manager/SKILL.md` |
| `product-sprint-prioritizer` | Atlas CEO | agency-shared | Agency-derived shared skill | Owned by Atlas CEO for executive decision support | converted | `hermes/shared-skills/agency/product-sprint-prioritizer/SKILL.md` |
| `product-trend-researcher` | Atlas CEO | agency-shared | Agency-derived shared skill | Owned by Atlas CEO for executive decision support | converted | `hermes/shared-skills/agency/product-trend-researcher/SKILL.md` |
| `sales-pipeline-analyst` | Atlas CEO, Marin | agency-shared | Agency-derived shared skill | Owned by Atlas CEO, Marin for executive decision support; marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-pipeline-analyst/SKILL.md` |
| `specialized-compliance-auditor` | Atlas CEO, Stet | agency-shared | Agency-derived shared skill | Advisory/readiness skill with current-source gates and human review. | converted-curated | `hermes/shared-skills/agency/specialized-compliance-auditor/SKILL.md` |
| `marketing-agentic-search-optimizer` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/marketing-agentic-search-optimizer/SKILL.md` |
| `marketing-ai-citation-strategist` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/marketing-ai-citation-strategist/SKILL.md` |
| `marketing-seo-specialist` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/marketing-seo-specialist/SKILL.md` |
| `sales-account-strategist` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-account-strategist/SKILL.md` |
| `sales-coach` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-coach/SKILL.md` |
| `sales-deal-strategist` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-deal-strategist/SKILL.md` |
| `sales-discovery-coach` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-discovery-coach/SKILL.md` |
| `sales-engineer` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-engineer/SKILL.md` |
| `sales-outbound-strategist` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-outbound-strategist/SKILL.md` |
| `sales-proposal-strategist` | Marin | agency-shared | Agency-derived shared skill | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | converted | `hermes/shared-skills/agency/sales-proposal-strategist/SKILL.md` |
| `marketing-linkedin-content-creator` | Marin, Quill | agency-shared | Agency-derived shared skill | Owned by Marin, Quill for marketing strategy, pipeline, and revenue-loop decisions; drafting, brand, content, and creative production support | converted | `hermes/shared-skills/agency/marketing-linkedin-content-creator/SKILL.md` |
| `engineering-backend-architect` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-backend-architect/SKILL.md` |
| `engineering-code-reviewer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-code-reviewer/SKILL.md` |
| `engineering-codebase-onboarding-engineer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-codebase-onboarding-engineer/SKILL.md` |
| `engineering-data-engineer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-data-engineer/SKILL.md` |
| `engineering-database-optimizer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-database-optimizer/SKILL.md` |
| `engineering-devops-automator` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-devops-automator/SKILL.md` |
| `engineering-email-intelligence-engineer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-email-intelligence-engineer/SKILL.md` |
| `engineering-incident-response-commander` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-incident-response-commander/SKILL.md` |
| `engineering-security-engineer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-security-engineer/SKILL.md` |
| `engineering-software-architect` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-software-architect/SKILL.md` |
| `engineering-sre` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-sre/SKILL.md` |
| `engineering-technical-writer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-technical-writer/SKILL.md` |
| `engineering-threat-detection-engineer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/engineering-threat-detection-engineer/SKILL.md` |
| `specialized-automation-governance-architect` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/specialized-automation-governance-architect/SKILL.md` |
| `specialized-lsp-index-engineer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/specialized-lsp-index-engineer/SKILL.md` |
| `specialized-mcp-builder` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/specialized-mcp-builder/SKILL.md` |
| `specialized-model-qa` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/specialized-model-qa/SKILL.md` |
| `testing-api-tester` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/testing-api-tester/SKILL.md` |
| `testing-workflow-optimizer` | Parked for future technical-operator | agency-shared | Agency-derived shared skill | future CTO / technical governance candidate; not active profile ownership | parked-candidate | `hermes/shared-skills/agency/testing-workflow-optimizer/SKILL.md` |
| `design-ui-designer` | Parked until artifact trigger | agency-shared | Agency-derived shared skill | valid creative/product workflow parked until a specific artifact needs it | parked-candidate | `hermes/shared-skills/agency/design-ui-designer/SKILL.md` |
| `design-ux-architect` | Parked until artifact trigger | agency-shared | Agency-derived shared skill | valid creative/product workflow parked until a specific artifact needs it | parked-candidate | `hermes/shared-skills/agency/design-ux-architect/SKILL.md` |
| `design-ux-researcher` | Parked until artifact trigger | agency-shared | Agency-derived shared skill | valid creative/product workflow parked until a specific artifact needs it | parked-candidate | `hermes/shared-skills/agency/design-ux-researcher/SKILL.md` |
| `design-whimsy-injector` | Parked until artifact trigger | agency-shared | Agency-derived shared skill | valid creative/product workflow parked until a specific artifact needs it | parked-candidate | `hermes/shared-skills/agency/design-whimsy-injector/SKILL.md` |
| `marketing-podcast-strategist` | Parked until artifact trigger | agency-shared | Agency-derived shared skill | valid creative/product workflow parked until a specific artifact needs it | parked-candidate | `hermes/shared-skills/agency/marketing-podcast-strategist/SKILL.md` |
| `marketing-reddit-community-builder` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/marketing-reddit-community-builder/SKILL.md` |
| `marketing-social-media-strategist` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/marketing-social-media-strategist/SKILL.md` |
| `marketing-twitter-engager` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/marketing-twitter-engager/SKILL.md` |
| `paid-media-auditor` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-auditor/SKILL.md` |
| `paid-media-creative-strategist` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-creative-strategist/SKILL.md` |
| `paid-media-paid-social-strategist` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-paid-social-strategist/SKILL.md` |
| `paid-media-ppc-strategist` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-ppc-strategist/SKILL.md` |
| `paid-media-programmatic-buyer` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-programmatic-buyer/SKILL.md` |
| `paid-media-search-query-analyst` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-search-query-analyst/SKILL.md` |
| `paid-media-tracking-specialist` | Parked until channel/tool trigger | agency-shared | Agency-derived shared skill | valid workflow parked until the current revenue loop authorizes the channel or spend surface | parked-candidate | `hermes/shared-skills/agency/paid-media-tracking-specialist/SKILL.md` |
| `design-image-prompt-engineer` | Quill | agency-shared | Agency-derived shared skill | Owned by Quill for drafting, brand, content, and creative production support | converted | `hermes/shared-skills/agency/design-image-prompt-engineer/SKILL.md` |
| `design-inclusive-visuals-specialist` | Quill | agency-shared | Agency-derived shared skill | Owned by Quill for drafting, brand, content, and creative production support | converted | `hermes/shared-skills/agency/design-inclusive-visuals-specialist/SKILL.md` |
| `design-visual-storyteller` | Quill | agency-shared | Agency-derived shared skill | Owned by Quill for drafting, brand, content, and creative production support | converted | `hermes/shared-skills/agency/design-visual-storyteller/SKILL.md` |
| `marketing-content-creator` | Quill | agency-shared | Agency-derived shared skill | Owned by Quill for drafting, brand, content, and creative production support | converted | `hermes/shared-skills/agency/marketing-content-creator/SKILL.md` |
| `design-brand-guardian` | Quill, Stet | agency-shared | Agency-derived shared skill | Owned by Quill, Stet for drafting, brand, content, and creative production support; pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/design-brand-guardian/SKILL.md` |
| `testing-accessibility-auditor` | Stet | agency-shared | Agency-derived shared skill | Owned by Stet for pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/testing-accessibility-auditor/SKILL.md` |
| `testing-evidence-collector` | Stet | agency-shared | Agency-derived shared skill | Owned by Stet for pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/testing-evidence-collector/SKILL.md` |
| `testing-performance-benchmarker` | Stet | agency-shared | Agency-derived shared skill | Owned by Stet for pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/testing-performance-benchmarker/SKILL.md` |
| `testing-reality-checker` | Stet | agency-shared | Agency-derived shared skill | Owned by Stet for pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/testing-reality-checker/SKILL.md` |
| `testing-test-results-analyzer` | Stet | agency-shared | Agency-derived shared skill | Owned by Stet for pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/testing-test-results-analyzer/SKILL.md` |
| `testing-tool-evaluator` | Stet | agency-shared | Agency-derived shared skill | Owned by Stet for pre-launch critique, verification, and risk review | converted | `hermes/shared-skills/agency/testing-tool-evaluator/SKILL.md` |
| `profile-from-template` | Fleet builder | platform | Hermes platform skill | profile scaffolding and capability creation | active | `hermes/skills/profile-from-template/SKILL.md` |
| `approval-proposal-draft` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/approval-proposal-draft.md` |
| `business-scorecard-brief` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/business-scorecard-brief.md` |
| `decision-memo` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/decision-memo.md` |
| `self-audit` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/self-audit.md` |
| `source-packet-triage` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/source-packet-triage.md` |
| `weekly-ceo-brief` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/weekly-ceo-brief.md` |
| `weekly-ceo-operating-loop` | Atlas CEO | profile-local | Hermes profile skill | executive decision support | active | `hermes/profiles/atlas-ceo/skills/weekly-ceo-operating-loop.md` |
| `aeo-opportunity-scout` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/aeo-opportunity-scout.md` |
| `buyer-signal-router` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/buyer-signal-router.md` |
| `campaign-brief-draft` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/campaign-brief-draft.md` |
| `kill-list-enforce` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/kill-list-enforce.md` |
| `self-audit` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/self-audit.md` |
| `supervised-dispatch` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/supervised-dispatch.md` |
| `weekly-review` | Marin | profile-local | Hermes profile skill | marketing strategy, pipeline, and revenue-loop decisions | active | `hermes/profiles/marin/skills/weekly-review.md` |
| `draft-campaign-asset` | Quill | profile-local | Hermes profile skill | drafting, brand, content, and creative production support | active | `hermes/profiles/quill/skills/draft-campaign-asset.md` |
| `draft-linkedin-field-note` | Quill | profile-local | Hermes profile skill | drafting, brand, content, and creative production support | active | `hermes/profiles/quill/skills/draft-linkedin-field-note.md` |
| `draft-outreach-message` | Quill | profile-local | Hermes profile skill | drafting, brand, content, and creative production support | active | `hermes/profiles/quill/skills/draft-outreach-message.md` |
| `revise-from-critique` | Quill | profile-local | Hermes profile skill | drafting, brand, content, and creative production support | active | `hermes/profiles/quill/skills/revise-from-critique.md` |
| `self-audit` | Quill | profile-local | Hermes profile skill | drafting, brand, content, and creative production support | active | `hermes/profiles/quill/skills/self-audit.md` |
| `critique-campaign-brief` | Stet | profile-local | Hermes profile skill | pre-launch critique, verification, and risk review | active | `hermes/profiles/stet/skills/critique-campaign-brief.md` |
| `critique-draft` | Stet | profile-local | Hermes profile skill | pre-launch critique, verification, and risk review | active | `hermes/profiles/stet/skills/critique-draft.md` |
| `critique-positioning` | Stet | profile-local | Hermes profile skill | pre-launch critique, verification, and risk review | active | `hermes/profiles/stet/skills/critique-positioning.md` |
| `pressure-test-campaign` | Stet | profile-local | Hermes profile skill | pre-launch critique, verification, and risk review | active | `hermes/profiles/stet/skills/pressure-test-campaign.md` |
| `self-audit` | Stet | profile-local | Hermes profile skill | pre-launch critique, verification, and risk review | active | `hermes/profiles/stet/skills/self-audit.md` |
| `generate-handoff` | All profiles | shared | Hermes shared skill | cross-session continuity | active | `hermes/shared-skills/generate-handoff/SKILL.md` |
| `email-triage` | Koho/Yeh future retainer profiles | shared | Hermes shared skill | read-only communications triage and proposal store | active | `hermes/shared-skills/email-triage/SKILL.md` |

## Every Agency Catalog Skill Addressed

| Source Skill | Recommended Owner | Fit | Priority | Status | Boundary |
| --- | --- | --- | --- | --- | --- |
| `academic/academic-anthropologist.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `academic/academic-geographer.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `academic/academic-historian.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `academic/academic-narratologist.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `academic/academic-psychologist.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `design/design-brand-guardian.md` | Quill, Stet | Owned by Quill, Stet for drafting, brand, content, and creative production support; pre-launch critique, verification, and risk review | P1 | converted | convert |
| `design/design-image-prompt-engineer.md` | Quill | Owned by Quill for drafting, brand, content, and creative production support | P1 | converted | convert |
| `design/design-inclusive-visuals-specialist.md` | Quill | Owned by Quill for drafting, brand, content, and creative production support | P1 | converted | convert |
| `design/design-ui-designer.md` | Parked until artifact trigger | valid creative/product workflow parked until a specific artifact needs it | P1 | converted | convert |
| `design/design-ux-architect.md` | Parked until artifact trigger | valid creative/product workflow parked until a specific artifact needs it | P1 | converted | convert |
| `design/design-ux-researcher.md` | Parked until artifact trigger | valid creative/product workflow parked until a specific artifact needs it | P1 | converted | convert |
| `design/design-visual-storyteller.md` | Quill | Owned by Quill for drafting, brand, content, and creative production support | P1 | converted | convert |
| `design/design-whimsy-injector.md` | Parked until artifact trigger | valid creative/product workflow parked until a specific artifact needs it | P1 | converted | convert |
| `engineering/engineering-ai-data-remediation-engineer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `engineering/engineering-ai-engineer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `engineering/engineering-autonomous-optimization-architect.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `engineering/engineering-backend-architect.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-cms-developer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `engineering/engineering-code-reviewer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-codebase-onboarding-engineer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-data-engineer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-database-optimizer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-devops-automator.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-email-intelligence-engineer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-embedded-firmware-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `engineering/engineering-feishu-integration-developer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `engineering/engineering-filament-optimization-specialist.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `engineering/engineering-frontend-developer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `engineering/engineering-git-workflow-master.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `engineering/engineering-incident-response-commander.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-minimal-change-engineer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `engineering/engineering-mobile-app-builder.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `engineering/engineering-rapid-prototyper.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `engineering/engineering-security-engineer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-senior-developer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `engineering/engineering-software-architect.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-solidity-smart-contract-engineer.md` | Future technical-operator candidate | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `engineering/engineering-sre.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-technical-writer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-threat-detection-engineer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `engineering/engineering-voice-ai-integration-engineer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `engineering/engineering-wechat-mini-program-developer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `finance/finance-bookkeeper-controller.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `finance/finance-financial-analyst.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `finance/finance-fpa-analyst.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `finance/finance-investment-researcher.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `finance/finance-tax-strategist.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | converted-curated | curate |
| `game-development/blender/blender-addon-engineer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `game-development/game-audio-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/game-designer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/godot/godot-gameplay-scripter.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/godot/godot-multiplayer-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/godot/godot-shader-developer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/level-designer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/narrative-designer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/roblox-studio/roblox-avatar-creator.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/roblox-studio/roblox-experience-designer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `game-development/roblox-studio/roblox-systems-scripter.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/technical-artist.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `game-development/unity/unity-architect.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/unity/unity-editor-tool-developer.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `game-development/unity/unity-multiplayer-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/unity/unity-shader-graph-artist.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `game-development/unreal-engine/unreal-multiplayer-architect.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/unreal-engine/unreal-systems-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `game-development/unreal-engine/unreal-technical-artist.md` | Future technical-operator candidate | Convertible later as a shared workflow; not installed into profile manifests yet. | P4 | cataloged | convert |
| `game-development/unreal-engine/unreal-world-builder.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-agentic-search-optimizer.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `marketing/marketing-ai-citation-strategist.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `marketing/marketing-app-store-optimizer.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `marketing/marketing-baidu-seo-specialist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-bilibili-content-strategist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-book-co-author.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `marketing/marketing-carousel-growth-engine.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `marketing/marketing-china-ecommerce-operator.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-china-market-localization-strategist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-content-creator.md` | Quill | Owned by Quill for drafting, brand, content, and creative production support | P1 | converted | convert |
| `marketing/marketing-cross-border-ecommerce.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P1 | cataloged | convert |
| `marketing/marketing-douyin-strategist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-growth-hacker.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `marketing/marketing-instagram-curator.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P1 | cataloged | convert |
| `marketing/marketing-kuaishou-strategist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-linkedin-content-creator.md` | Marin, Quill | Owned by Marin, Quill for marketing strategy, pipeline, and revenue-loop decisions; drafting, brand, content, and creative production support | P1 | converted | convert |
| `marketing/marketing-livestream-commerce-coach.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-podcast-strategist.md` | Parked until artifact trigger | valid creative/product workflow parked until a specific artifact needs it | P1 | converted | convert |
| `marketing/marketing-private-domain-operator.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-reddit-community-builder.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `marketing/marketing-seo-specialist.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `marketing/marketing-short-video-editing-coach.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P1 | cataloged | convert |
| `marketing/marketing-social-media-strategist.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `marketing/marketing-tiktok-strategist.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P1 | cataloged | convert |
| `marketing/marketing-twitter-engager.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `marketing/marketing-video-optimization-specialist.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `marketing/marketing-wechat-official-account.md` | Marin | Convertible later as a shared workflow; not installed into profile manifests yet. | P1 | cataloged | convert |
| `marketing/marketing-weibo-strategist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-xiaohongshu-specialist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `marketing/marketing-zhihu-strategist.md` | Marin | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `paid-media/paid-media-auditor.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `paid-media/paid-media-creative-strategist.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `paid-media/paid-media-paid-social-strategist.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `paid-media/paid-media-ppc-strategist.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `paid-media/paid-media-programmatic-buyer.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `paid-media/paid-media-search-query-analyst.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `paid-media/paid-media-tracking-specialist.md` | Parked until channel/tool trigger | valid workflow parked until the current revenue loop authorizes the channel or spend surface | P1 | converted | convert |
| `product/product-behavioral-nudge-engine.md` | Atlas CEO | Owned by Atlas CEO for executive decision support | P1 | converted | convert |
| `product/product-feedback-synthesizer.md` | Atlas CEO | Owned by Atlas CEO for executive decision support | P1 | converted | convert |
| `product/product-manager.md` | Atlas CEO | Owned by Atlas CEO for executive decision support | P1 | converted | convert |
| `product/product-sprint-prioritizer.md` | Atlas CEO | Owned by Atlas CEO for executive decision support | P1 | converted | convert |
| `product/product-trend-researcher.md` | Atlas CEO | Owned by Atlas CEO for executive decision support | P1 | converted | convert |
| `project-management/project-management-experiment-tracker.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `project-management/project-management-jira-workflow-steward.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `project-management/project-management-project-shepherd.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `project-management/project-management-studio-operations.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `project-management/project-management-studio-producer.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `project-management/project-manager-senior.md` | Atlas CEO | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `sales/sales-account-strategist.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-coach.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-deal-strategist.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-discovery-coach.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-engineer.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-outbound-strategist.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-pipeline-analyst.md` | Atlas CEO, Marin | Owned by Atlas CEO, Marin for executive decision support; marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `sales/sales-proposal-strategist.md` | Marin | Owned by Marin for marketing strategy, pipeline, and revenue-loop decisions | P1 | converted | convert |
| `spatial-computing/macos-spatial-metal-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `spatial-computing/terminal-integration-specialist.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `spatial-computing/visionos-spatial-engineer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `spatial-computing/xr-cockpit-interaction-specialist.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `spatial-computing/xr-immersive-developer.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `spatial-computing/xr-interface-architect.md` | Future technical-operator candidate | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/accounts-payable-agent.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/agentic-identity-trust.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/agents-orchestrator.md` | No owner - keep as profile/agent boundary reference | Do not convert; this is a coordinator or identity role, not procedural memory. | P5 | blocked-role-boundary | keep out of profiles |
| `specialized/automation-governance-architect.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `specialized/blockchain-security-auditor.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/compliance-auditor.md` | Atlas CEO, Stet | Advisory/readiness skill with current-source gates and human review. | P3 | converted-curated | curate |
| `specialized/corporate-training-designer.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/customer-service.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/data-consolidation-agent.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/government-digital-presales-consultant.md` | Atlas CEO or future technical-operator by request | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/healthcare-customer-service.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/healthcare-marketing-compliance.md` | Atlas CEO or future technical-operator by request | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/hospitality-guest-services.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/hr-onboarding.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/identity-graph-operator.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/language-translator.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/legal-billing-time-tracking.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/legal-client-intake.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/legal-document-review.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/loan-officer-assistant.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P3 | cataloged | convert |
| `specialized/lsp-index-engineer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `specialized/real-estate-buyer-seller.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/recruitment-specialist.md` | Atlas CEO or future technical-operator by request | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/report-distribution-agent.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/retail-customer-returns.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/sales-data-extraction-agent.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/sales-outreach.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/specialized-chief-of-staff.md` | No owner - keep as profile/agent boundary reference | Do not convert; this is a coordinator or identity role, not procedural memory. | P5 | blocked-role-boundary | keep out of profiles |
| `specialized/specialized-civil-engineer.md` | Atlas CEO or future technical-operator by request | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `specialized/specialized-cultural-intelligence-strategist.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/specialized-developer-advocate.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/specialized-document-generator.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/specialized-french-consulting-market.md` | Atlas CEO or future technical-operator by request | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/specialized-korean-business-navigator.md` | Atlas CEO or future technical-operator by request | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/specialized-mcp-builder.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `specialized/specialized-model-qa.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `specialized/specialized-salesforce-architect.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/specialized-workflow-architect.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/study-abroad-advisor.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `specialized/supply-chain-strategist.md` | Atlas CEO or future technical-operator by request | Reference-only until a live project or client workflow needs it. | P4 | deferred | defer |
| `specialized/zk-steward.md` | Atlas CEO or future technical-operator by request | Convertible later as a shared workflow; not installed into profile manifests yet. | P2 | cataloged | convert |
| `support/support-analytics-reporter.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `support/support-executive-summary-generator.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `support/support-finance-tracker.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `support/support-infrastructure-maintainer.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `support/support-legal-compliance-checker.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `support/support-support-responder.md` | Atlas CEO | Advisory/readiness skill with current-source gates and human review. | P3 | cataloged | curate |
| `testing/testing-accessibility-auditor.md` | Stet | Owned by Stet for pre-launch critique, verification, and risk review | P1 | converted | convert |
| `testing/testing-api-tester.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |
| `testing/testing-evidence-collector.md` | Stet | Owned by Stet for pre-launch critique, verification, and risk review | P1 | converted | convert |
| `testing/testing-performance-benchmarker.md` | Stet | Owned by Stet for pre-launch critique, verification, and risk review | P1 | converted | convert |
| `testing/testing-reality-checker.md` | Stet | Owned by Stet for pre-launch critique, verification, and risk review | P1 | converted | convert |
| `testing/testing-test-results-analyzer.md` | Stet | Owned by Stet for pre-launch critique, verification, and risk review | P1 | converted | convert |
| `testing/testing-tool-evaluator.md` | Stet | Owned by Stet for pre-launch critique, verification, and risk review | P1 | converted | convert |
| `testing/testing-workflow-optimizer.md` | Parked for future technical-operator | future CTO / technical governance candidate; not active profile ownership | P1 | converted | convert |

## Reading The Map

- `Owner` means the profile that should reach for the skill first.
- `Shared` means the skill can be used by multiple profiles but should still be invoked through the owning profile's boundaries.
- `Deferred` means it is intentionally visible but not installed until a real project asks for it.
- `Blocked` means it would blur the profile-vs-skill boundary and should stay out of the skill arsenal.
