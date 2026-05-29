// build-prompt.mjs — shared promptfoo prompt builder for the Research Scout Fleet
// eval harness.
//
// The rapid eval loop must exercise each scout's REAL runtime instructions so a
// refinement to SOUL/DOCTRINE/topic-sweep moves the eval number. This function
// assembles the synthesis prompt from the scout's live profile docs and injects
// the fixture as the "swept sources" block that /research-stack would otherwise
// produce — so the model runs the cheap deterministic chain (dedup → classify →
// verdict → digest-shape → source-grounding) with zero network and zero NotebookLM.
//
// promptfoo contract: `prompts: - file://../../_shared/scout-eval/build-prompt.mjs`
// in each scout's eval/promptfoo.yaml. promptfoo calls this with { vars } where
// vars.profile names the scout dir and vars.fixture holds the loaded fixture text.
// Returns an OpenAI-style chat messages array (system = instructions, user = sweep).

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const HERE = dirname(fileURLToPath(import.meta.url)); // profiles/_shared/scout-eval
const PROFILES_DIR = resolve(HERE, "..", ".."); // profiles/

function readDoc(profile, rel) {
  try {
    return readFileSync(resolve(PROFILES_DIR, profile, rel), "utf8").trim();
  } catch {
    return "";
  }
}

export default async function buildPrompt({ vars }) {
  const profile = vars.profile;
  if (!profile) {
    throw new Error(
      "scout-eval build-prompt: vars.profile is required (set defaultTest.vars.profile in promptfoo.yaml)",
    );
  }

  const soul = readDoc(profile, "SOUL.md");
  const doctrine = readDoc(profile, "DOCTRINE.md");
  const skill = readDoc(profile, "skills/topic-sweep.md");
  const fixture = (vars.fixture || "").toString().trim();

  // System = the scout's live persona + doctrine + the skill's procedure/contract.
  // This is the exact instruction surface a prompt-refinement loop edits.
  const system = [
    soul,
    "\n\n---\n\n",
    doctrine,
    "\n\n---\n\n",
    skill,
  ].join("");

  // User = the fixture as the already-swept, already-compressed source bundle,
  // plus the explicit instruction to skip the live sweep and synthesize now.
  const user = [
    "You are running the `topic-sweep` skill, but the live `/research-stack`",
    "step has ALREADY been performed for you. The compressed source bundle below",
    "is exactly what that step produced — treat it as your swept sources for this",
    "cycle. Do NOT call /research-stack, NotebookLM, or any tool. Do the cheap",
    "deterministic chain only: dedup against what you already know, classify each",
    "candidate against the CI verdict rubric, apply the reversibility lens, and",
    "produce the digest in the `DOCTRINE.md § Output contract` shape — numbered",
    "findings, each citing a source from the bundle, each ending with exactly one",
    "verdict + a named target. If the bundle contains nothing new, report a quiet",
    "week honestly and invent no findings.",
    "\n\n## Swept sources (since last digest)\n\n",
    fixture,
  ].join(" ").replace(" \n\n", "\n\n");

  return [
    { role: "system", content: system },
    { role: "user", content: user },
  ];
}
