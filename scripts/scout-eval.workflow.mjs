// scout-eval.workflow.mjs — Research Scout Fleet eval fan-out.
//
// Versioned source for the Workflow-tool run (NOT a standalone node script — the
// agent()/pipeline()/parallel() API only exists inside Claude Code's Workflow
// runtime). Run it with:  Workflow({ scriptPath: "scripts/scout-eval.workflow.mjs",
// args: { runs: 20 } })
//
// Separation of concerns: promptfoo (inside scout-eval.sh, via --repeat N) does the
// cheap deterministic scoring at high N; agents do the parallel orchestration plus
// the qualitative failure-clustering promptfoo can't. Agent count stays ~9 while N
// stays high.
//
// Run → Cluster → Synthesize:
//   Run       — one agent per scout shells `scout-eval.sh <scout> --runs N --json`.
//   Cluster   — per scout with failures, group them into themes mapped to the
//               editable surface (SOUL / DOCTRINE line / topic-sweep step).
//   Synthesize— cross-scout variance table + ranked clusters + per-scout gate +
//               recommended prompt edits.

export const meta = {
  name: "scout-eval-fleet",
  description:
    "Run the Research Scout Fleet eval across 4 scouts × fixtures × N runs, cluster failures, synthesize variance + gate verdict",
  phases: [
    { title: "Run", detail: "one agent per scout runs scout-eval.sh --json" },
    { title: "Cluster", detail: "cluster each scout's failures into editable-surface themes" },
    { title: "Synthesize", detail: "cross-scout variance + ranked clusters + gate verdict" },
  ],
};

const REPO = "/Users/alexhale/Projects/agents";
const SCOUTS = ["hermes-scout", "cc-scout", "mcp-scout", "pkm-scout"];
const N = (args && args.runs) || 20;

const RUN_SCHEMA = {
  type: "object",
  required: ["scout", "gate", "providers", "failures"],
  properties: {
    scout: { type: "string" },
    gate: { type: "string", enum: ["PASS", "FAIL"] },
    providers: {
      type: "array",
      items: {
        type: "object",
        required: ["label", "rate", "wilson_lower_ci", "smoke"],
        properties: {
          label: { type: "string" },
          rate: { type: "number" },
          wilson_lower_ci: { type: "number" },
          smoke: { type: "boolean" },
        },
      },
    },
    failures: {
      type: "array",
      items: {
        type: "object",
        required: ["provider", "fixture", "reason"],
        properties: {
          provider: { type: "string" },
          fixture: { type: "string" },
          reason: { type: "string" },
        },
      },
    },
  },
};

const CLUSTER_SCHEMA = {
  type: "object",
  required: ["scout", "clusters"],
  properties: {
    scout: { type: "string" },
    clusters: {
      type: "array",
      items: {
        type: "object",
        required: ["theme", "surface", "fixtures", "count", "recommended_edit"],
        properties: {
          theme: { type: "string", description: "the shared failure pattern" },
          surface: {
            type: "string",
            enum: ["SOUL", "DOCTRINE", "topic-sweep", "fixture", "rubric"],
            description: "which editable file the fix lands in",
          },
          fixtures: { type: "array", items: { type: "string" } },
          count: { type: "number" },
          recommended_edit: { type: "string", description: "the concrete one-line change to try" },
        },
      },
    },
  },
};

const SYNTH_SCHEMA = {
  type: "object",
  required: ["fleet_gate", "variance", "ranked_clusters", "next_move"],
  properties: {
    fleet_gate: { type: "string", enum: ["PASS", "FAIL"], description: "PASS only if every scout's gate is PASS" },
    variance: {
      type: "array",
      description: "one row per scout × provider",
      items: {
        type: "object",
        required: ["scout", "provider", "rate", "wilson_lower_ci", "gate"],
        properties: {
          scout: { type: "string" },
          provider: { type: "string" },
          rate: { type: "number" },
          wilson_lower_ci: { type: "number" },
          gate: { type: "string" },
        },
      },
    },
    ranked_clusters: {
      type: "array",
      description: "failure clusters across the fleet, highest-impact first",
      items: {
        type: "object",
        required: ["rank", "theme", "surface", "scouts", "recommended_edit"],
        properties: {
          rank: { type: "number" },
          theme: { type: "string" },
          surface: { type: "string" },
          scouts: { type: "array", items: { type: "string" } },
          recommended_edit: { type: "string" },
        },
      },
    },
    next_move: { type: "string", description: "the single highest-leverage refinement to make next, with its gate" },
  },
};

// Run + Cluster as a pipeline (no barrier between scouts): each scout's failures
// cluster as soon as its run finishes.
phase("Run");
const perScout = await pipeline(
  SCOUTS,
  (scout) =>
    agent(
      `Run this exact command and capture stdout:\n\n` +
        `cd ${REPO} && bash scripts/scout-eval.sh ${scout} --runs ${N} --json\n\n` +
        `The command prints progress on stderr and a single JSON object on stdout ` +
        `(keys: gate, gate_threshold, gate_providers, providers, failures). Parse that ` +
        `JSON and return it mapped to the schema: scout="${scout}", gate, a providers[] ` +
        `array (label/rate/wilson_lower_ci/smoke from the providers object), and the ` +
        `failures[] array (provider/fixture/reason). If the command errors, return ` +
        `gate="FAIL" with an empty providers/failures and the error in a failure reason.`,
      { label: `run:${scout}`, phase: "Run", schema: RUN_SCHEMA },
    ),
  (run, scout) => {
    if (!run || !run.failures || run.failures.length === 0) {
      return { scout, run: run || null, clusters: [] };
    }
    return agent(
      `Cluster these eval failures for the ${scout} Research Scout into shared themes.\n\n` +
        `Each scout's prompt is assembled from its live SOUL.md + DOCTRINE.md + ` +
        `skills/topic-sweep.md (under ${REPO}/hermes/profiles/${scout}/). Map each ` +
        `cluster to the single editable surface whose change would most likely fix it.\n\n` +
        `Failures:\n${JSON.stringify(run.failures, null, 2)}\n\n` +
        `Return clusters with theme, surface, the fixtures involved, count, and a ` +
        `concrete one-line recommended_edit.`,
      { label: `cluster:${scout}`, phase: "Cluster", schema: CLUSTER_SCHEMA },
    ).then((c) => ({ scout, run, clusters: c.clusters || [] }));
  },
);

phase("Synthesize");
const synth = await agent(
  `Synthesize the Research Scout Fleet eval run (N=${N} repeats per fixture).\n\n` +
    `Per-scout results + failure clusters:\n${JSON.stringify(perScout, null, 2)}\n\n` +
    `Produce: fleet_gate (PASS only if every scout gate is PASS); a variance table ` +
    `(one row per scout×provider with rate, wilson_lower_ci, and whether it clears ` +
    `the 80% bar); ranked_clusters across the whole fleet (highest-impact first, ` +
    `each naming the editable surface + recommended_edit); and the single ` +
    `next_move — the highest-leverage refinement to make next and the gate it must ` +
    `hold (≥80% on sonnet AND haiku).`,
  { label: "synthesize", phase: "Synthesize", schema: SYNTH_SCHEMA },
);

return { n: N, perScout, synthesis: synth };
