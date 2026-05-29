# Swept sources — Hermes runtime (synthetic fixture: active week)

> Synthetic eval fixture. Stands in for the compressed source bundle that
> `/research-stack --deep --youtube` would return. All URLs/versions are
> fabricated for testing the scout's classify → verdict → digest chain.

## S1 — Hermes Agent v0.15.0 release notes
- URL: https://hermes-agent.nousresearch.com/docs/releases/v0-15-0
- Date: 2026-05-27
- Summary: Adds a first-class `skill.eval` block to `config.yaml` so a profile
  can declare an acceptance eval inline. Backward compatible; opt-in. Not present
  in the capability roadmap. New since last digest.

## S2 — oh-my-hermes (witt3rd/oh-my-hermes) adds a `ralplan` retry policy
- URL: https://github.com/witt3rd/oh-my-hermes/releases/tag/v2.3.0
- Date: 2026-05-26
- Summary: Community pattern — a declarative retry/backoff policy for skill calls,
  shipped as a drop-in YAML fragment. Several fleet profiles hand-roll retries
  today. Reversible to try in one profile. New.

## S3 — Jack Roberts (Lane-2 creator) on profile-per-topic scouts
- URL: https://www.youtube.com/watch?v=hermesScoutPattern2026
- Date: 2026-05-25
- Summary: Walkthrough of running one narrow scout per topic with a weekly digest,
  matching the fleet's current shape. Confirms the approach; nothing to change.
  Technique is real, not demo-bait, but it's a validation, not a new move.

## S4 — awesome-hermes-agent index movement
- URL: https://github.com/0xNyk/awesome-hermes-agent/commits/main
- Date: 2026-05-24
- Summary: Three new community repos indexed this week; none materially different
  from patterns already tracked in the capability roadmap.
