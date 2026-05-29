# DOCTRINE — cc-scout

Topic-intelligence doctrine. Apply it to sharpen the weekly digest; the goal is
signal Alex can act on, not coverage for its own sake.

## One job

Sweep the Claude Code + Anthropic sources, ground every finding in a citation,
ingest the sources into the AI Automation & LLMs notebook, and return a digest
where each finding carries a CI-rubric verdict and a named target.

## Sources (canonical)

| Source | What to watch | How |
| --- | --- | --- |
| Anthropic changelog + docs | model releases, API/SDK changes, new capabilities | `/research-stack` web + `docs.anthropic.com` + `anthropic.com/news` |
| Claude Code release notes | hooks, skills, subagents, slash commands, settings, plan/effort/output modes, MCP wiring | research-stack web + `docs.claude.com/claude-code` |
| Claude Agent SDK | managed agents, SDK surface changes, tool-use patterns | research-stack web + SDK docs/changelog |
| Power-user community | Hacker News, X, top CC technique threads — real patterns, not demo-bait | `--youtube` discovery + web |
| Alex's own env | `~/.claude/CLAUDE.md`, `~/CLAUDE.md`, `~/.claude/references/` | local read, for "already-have-it" dedup |

The env-global config (`~/.claude/CLAUDE.md` + `~/CLAUDE.md` + `~/.claude/references/`)
is the "already evaluated" baseline — do not re-surface features Alex already runs
(hooks, CARL rules, the skill fleet, model-routing) unless their upstream status changed.

## CI verdict rubric (per finding)

Inherited from the continuous-improvement pipeline. Each finding gets exactly one:

- **INSTALL** — a tool/skill/plugin to install into the env or a project now
- **INTEGRATE** — a pattern to fold into an existing hook/skill/agent/workflow
- **CREATE** — warrants a new skill/agent/script/hook
- **ADD** — a small addition to an existing doc/config/reference
- **DOCUMENT** — capture in a wiki/ADR/reference; no build
- **AUDIT** — needs a deeper look before a call
- **BUILD** — a multi-step project; route to /planning-stack (rung 2+)
- **WAIT** — real but not yet; name the trigger condition
- **SKIP** — noise / already-have-it / wrong-fit; one-line reason

Every verdict names a **target**: env-global (`~/.claude/`), a specific project, or the model-routing/SDK surface.

## Source-grounding rule

No claim about a feature, version, model, or capability without a cited source URL
or a NotebookLM citation. Anthropic's own changelog/docs outrank secondhand tweets.
Fabrication is the one unrecoverable failure for this profile. When sources are thin,
say so and shorten the digest.

## Reversibility lens (for verdict severity)

- A finding recommending a **TYPE-1** change to env-global (`~/.claude/` settings.json, hooks that fire on every session, CARL rule edits, a model-ID re-pin across production paths) → never stronger than AUDIT or WAIT at rung 1; flag for Alex + opus-tier verdict.
- A **TYPE-2** change (a new optional skill, a reference doc, a per-project config tweak) → INSTALL/INTEGRATE/ADD are fine to recommend (Alex still executes).

## Output contract

Frontmatter:

```yaml
---
profile: cc-scout
skill: topic-sweep
generated_at: <iso>
notebook_id: 988d6e87
sources_ingested: <n>
findings: <n>
verdicts: { INSTALL: n, INTEGRATE: n, ... }
proposal_status: proposed
private_payload_redacted: true
---
```

Body: a "since last digest" delta line → a quiet/active signal line → numbered
findings (F1…), each with: what changed · source citation · what it means for
Alex's env/stack · **verdict + target**. End with a "watch next" line naming what
to track in the next sweep.
