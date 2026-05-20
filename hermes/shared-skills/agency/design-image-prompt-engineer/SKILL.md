---
name: design-image-prompt-engineer
description: Use when a Hermes profile needs the Agency-derived Image Prompt Engineer workflow. Expert photography prompt engineer specializing in crafting detailed, evocative prompts for AI image generation. Masters the art of translating visual concepts into precise language that produces stunning, professional-quality photography through generative AI tools.
---

# Image Prompt Engineer

This is a converted Agency catalog workflow. Use it as procedural support inside an existing Hermes profile; do not adopt the original agent persona.

## Use When

- The request asks for image prompt engineer style help, assessment, planning, critique, or artifact production.
- The active profile has opted into `design-image-prompt-engineer` in `hermes/shared-skills/agency/CATALOG.md`.
- The work can remain proposal-only, read-only, or manually reviewed by Alex.

## Inputs

- User goal and success criteria.
- Relevant source files, URLs, screenshots, metrics, logs, or evidence package.
- Explicit constraints: audience, scope, deadline, brand/compliance rules, and what must not happen.
- Current date and source freshness when claims may change over time.

## Procedure

1. Restate the task as a bounded workflow and name any missing inputs.
2. Gather only the sources needed for the requested artifact; prefer repo/vault truth over generic advice.
3. Apply the upstream workflow shape from the Agency source, but remove persona language and unsupported authority.
4. Produce the deliverable in the output contract below.
5. Run the validation checks and clearly mark any unresolved risk.

## Output Contract

Return a design critique or proposal with concrete surfaces, rationale, and acceptance checks. Do not invent brand rules; cite the available brand source.

## Constraints

- Use this as a skill workflow, not as a persona or standalone agent.
- Do not create new Hermes profiles, dispatch agents, or claim persistent memory.
- Do not add external-send, publishing, money-movement, or unattended automation authority.
- State missing inputs instead of inventing facts, metrics, legal requirements, or source evidence.

## Validation

- Every factual claim has a source, input, or explicit assumption.
- The output contains a clear verdict, recommendation, or next manual action.
- The output does not claim execution, persistence, external sending, publishing, or spend.
- High-stakes claims are caveated and require current-source verification before action.

## Source Attribution

- Adapted from `design/design-image-prompt-engineer.md` in `msitarzewski/agency-agents` at commit `783f6a7`.
- Original catalog license: MIT.
- Conversion note: persona, memory, and autonomous-agent framing were intentionally removed.
