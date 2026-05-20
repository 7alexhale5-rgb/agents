---
name: sales-coach
description: Use when a Hermes profile needs the Agency-derived Sales Coach workflow. Expert sales coaching specialist focused on rep development, pipeline review facilitation, call coaching, deal strategy, and forecast accuracy. Makes every rep and every deal better through structured coaching methodology and behavioral feedback.
---

# Sales Coach

This is a converted Agency catalog workflow. Use it as procedural support inside an existing Hermes profile; do not adopt the original agent persona.

## Use When

- The request asks for sales coach style help, assessment, planning, critique, or artifact production.
- The active profile has opted into `sales-coach` in `hermes/shared-skills/agency/CATALOG.md`.
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

Return an advisory memo or worksheet only. Include source notes, assumptions, risks, and the smallest next manual action. Do not publish, send, schedule, spend, scrape at scale, or create unattended outreach.

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

- Adapted from `sales/sales-coach.md` in `msitarzewski/agency-agents` at commit `783f6a7`.
- Original catalog license: MIT.
- Conversion note: persona, memory, and autonomous-agent framing were intentionally removed.
