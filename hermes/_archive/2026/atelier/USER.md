# USER — for atelier profile

The operator is **Alex Hale** (`alex@kohoconsulting.com`). Founder, designer-engineer,
ships across ~20 projects rooted at `~/Projects/<kebab-case>/` per the filesystem
protocol (`~/Projects/FILESYSTEM-PROTOCOL.md`).

## Stack tilts

- **Default frontend**: Next.js App Router + Tailwind + shadcn/ui + Radix primitives
- **Exception**: `koho/consult-ops/` uses Vite + React. `prettyfly-os/` is the PrettyFly OS command surface for the PrettyFly Runtime agentic model replacement and uses Next.js. Match the project; do not migrate.
- **Color model**: HSL CSS variables. Warm-light + zinc-dark palette tradition.
- **Typography**: Geist Sans + Geist Mono baseline; project-specific overrides in `DESIGN.md` only.
- **Components**: shadcn/ui as foundation; project-specific extensions live in
  `components/ui/` and reference `DESIGN.md` tokens by name.

## Decision-making style

- Throwaway-first (Karpathy ladder cadence) — build the dumbest end-to-end, instrument after.
- Per-project `DESIGN.md` is the **contract**; `.interface-design/system.md` is the **rationale**.
- Never inline hex outside `DESIGN.md`. Every color is a token reference.
- Tokens are versioned with the project; design changes ship as PRs, not patches.
- Reference impl when in doubt: `~/Projects/koho/consult-ops/DESIGN.md` (gold-standard).
- Three-layer convention is mandatory for any UI-bearing project — see
  `~/Projects/CLAUDE.md` § Per-Project Design System.

## Communication

- Tight prose. No emoji. No fluff. No trailing summaries — Alex reads the diff.
- Lead with the answer; supporting evidence after.
- Quote token names (e.g., `--color-surface-2`), not hex values, in any review or audit.
- When proposing a change, name the file path (absolute) and the precise line/section.

## Project context

Alex's project registry: `~/Projects/MANIFEST.md`. The mutation allowlist in
`config.yaml` covers the UI-bearing projects with active design work. New projects
require an explicit allowlist update before Atelier can mutate them.
