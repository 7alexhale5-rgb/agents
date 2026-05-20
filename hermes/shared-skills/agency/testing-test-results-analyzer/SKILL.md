---
name: testing-test-results-analyzer
description: Use when a Hermes profile needs the Agency-derived Test Results Analyzer workflow. Expert test analysis specialist focused on comprehensive test result evaluation, quality metrics analysis, and actionable insight generation from testing activities
---

# Test Results Analyzer

This is a converted Agency catalog workflow. Use it as procedural support inside an existing Hermes profile; do not adopt the original agent persona.

## Use When

- The request asks for test results analyzer style help, assessment, planning, critique, or artifact production.
- The active profile has opted into `testing-test-results-analyzer` in `hermes/shared-skills/agency/CATALOG.md`.
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

Return an evidence-first verdict with commands run, artifacts inspected, blocking gaps, and the exact evidence needed to certify the work.

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

- Adapted from `testing/testing-test-results-analyzer.md` in `msitarzewski/agency-agents` at commit `783f6a7`.
- Original catalog license: MIT.
- Conversion note: persona, memory, and autonomous-agent framing were intentionally removed.
