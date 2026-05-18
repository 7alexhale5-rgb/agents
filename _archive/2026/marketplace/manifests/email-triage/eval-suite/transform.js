// Promptfoo transform: parse the LLM's raw text output into { category, urgency }.
// Tolerates: surrounding markdown fences, leading/trailing prose, whitespace.
// On parse failure, returns a sentinel that will fail the equals assertion.

module.exports = (output, _context) => {
  if (typeof output !== "string") {
    return { category: "parse_error", urgency: 0, raw: String(output) };
  }

  // Strip markdown code fences if present
  let s = output.trim();
  s = s.replace(/^```(?:json)?\s*/i, "").replace(/\s*```\s*$/i, "");

  // Find the first {...} JSON object in the string (in case the model added prose)
  const match = s.match(/\{[\s\S]*?\}/);
  if (!match) {
    return { category: "no_json_found", urgency: 0, raw: output };
  }

  try {
    const parsed = JSON.parse(match[0]);
    const category = String(parsed.category || "")
      .toLowerCase()
      .trim();
    const urgency = Number(parsed.urgency);
    return {
      category: ["respond", "deferred", "unsubscribe", "delete"].includes(
        category,
      )
        ? category
        : `invalid:${category}`,
      urgency: Number.isFinite(urgency) ? urgency : 0,
      raw: output,
    };
  } catch (e) {
    return {
      category: "parse_error",
      urgency: 0,
      raw: output,
      error: e.message,
    };
  }
};
