#!/usr/bin/env node
/**
 * 4d-senses MCP server
 * Stdio JSON-RPC. Exposes 5 read-only tools that wrap Alex's existing hook state.
 *
 * Senses live at ~/.claude/hooks/ (sense-1-sight, sense-5-rhythm, sense-8-smell,
 * sense-10-pain, sense-15-intuition) plus ~/.claude/scripts/4d-auto-vision.py
 * and ~/.claude/scripts/watch-video.py. Their persistent state is the source of
 * truth; this MCP just reads it.
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { readFile, readdir, stat } from "fs/promises";
import { existsSync } from "fs";
import { homedir } from "os";
import { join } from "path";

const HOME = homedir();
const HOOKS_DIR = join(HOME, ".claude", "hooks");
const SENSE_LIB = join(HOOKS_DIR, "_sense-lib");
const SCRIPTS_DIR = join(HOME, ".claude", "scripts");
const VISION_DIR = "/tmp/video-intelligence";
const SMELL_LOG = join(SENSE_LIB, "smell.log");
const PAIN_LOG = join(SENSE_LIB, "pain.log");
const INTUITION_DB = join(SENSE_LIB, "intuition.jsonl");

// ---------- helpers ----------

async function tail(path, hours = 24) {
  if (!existsSync(path)) return { entries: [], note: `no log at ${path} yet` };
  const txt = await readFile(path, "utf-8");
  const lines = txt.split("\n").filter(Boolean);
  const cutoff = Date.now() - hours * 3600 * 1000;
  const recent = lines.filter((l) => {
    const m = l.match(/^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})/);
    if (!m) return true;
    return new Date(m[1]).getTime() >= cutoff;
  });
  return {
    entries: recent.slice(-50),
    note: `${recent.length} entries in last ${hours}h`,
  };
}

async function latestVisionReport() {
  if (!existsSync(VISION_DIR)) return null;
  const dirs = await readdir(VISION_DIR);
  let latest = null;
  let latestMtime = 0;
  for (const d of dirs) {
    const path = join(VISION_DIR, d);
    try {
      const s = await stat(path);
      if (s.isDirectory() && s.mtimeMs > latestMtime) {
        latestMtime = s.mtimeMs;
        latest = path;
      }
    } catch {}
  }
  if (!latest) return null;
  const reportPath = join(latest, "gemini_perception.md");
  if (existsSync(reportPath)) {
    const md = await readFile(reportPath, "utf-8");
    return {
      path: latest,
      report: md.slice(0, 8000),
      truncated: md.length > 8000,
    };
  }
  return {
    path: latest,
    report: "(no gemini_perception.md yet — vision still processing)",
    truncated: false,
  };
}

function intuitionMatch(text, entries) {
  if (!entries || !text) return [];
  const needle = text.toLowerCase();
  const tokens = needle.split(/\W+/).filter((t) => t.length > 3);
  if (!tokens.length) return [];
  return entries
    .map((e) => {
      const haystack = (e.text || "").toLowerCase();
      const hits = tokens.filter((t) => haystack.includes(t)).length;
      return { entry: e, score: hits };
    })
    .filter((m) => m.score >= 2)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);
}

async function readIntuitionDb() {
  if (!existsSync(INTUITION_DB)) return [];
  const txt = await readFile(INTUITION_DB, "utf-8");
  return txt
    .split("\n")
    .filter(Boolean)
    .map((l) => {
      try {
        return JSON.parse(l);
      } catch {
        return null;
      }
    })
    .filter(Boolean);
}

// ---------- MCP server ----------

const server = new Server(
  { name: "4d-senses", version: "1.0.0" },
  { capabilities: { tools: {} } },
);

const TOOLS = [
  {
    name: "smell_recent",
    description:
      "Recent code-smell warnings from sense-8-smell hook (god files, deep nesting, duplication, secrets, TODOs).",
    inputSchema: {
      type: "object",
      properties: {
        window_hours: {
          type: "integer",
          default: 24,
          description: "Lookback window in hours",
        },
      },
    },
  },
  {
    name: "pain_active",
    description:
      "Active pain incidents from sense-10-pain hook (repeated failure patterns, auto-checkpoints).",
    inputSchema: {
      type: "object",
      properties: {
        window_hours: { type: "integer", default: 24 },
      },
    },
  },
  {
    name: "intuition_for_pattern",
    description:
      "Match a piece of text or planned action against the intuition database (past feedback, risky-pattern warnings). Returns up to 5 best matches.",
    inputSchema: {
      type: "object",
      properties: {
        text: {
          type: "string",
          description: "Text to check for pattern matches",
        },
      },
      required: ["text"],
    },
  },
  {
    name: "vision_latest",
    description:
      "Latest 4D-auto-vision report (frame analysis from a recent video URL). Returns gemini_perception.md content if processing is done, status note otherwise.",
    inputSchema: { type: "object", properties: {} },
  },
  {
    name: "status",
    description:
      "One-page summary across all 4 senses — counts, alert level, what is currently firing.",
    inputSchema: { type: "object", properties: {} },
  },
];

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args = {} } = req.params;

  try {
    if (name === "smell_recent") {
      const out = await tail(SMELL_LOG, args.window_hours || 24);
      return {
        content: [{ type: "text", text: JSON.stringify(out, null, 2) }],
      };
    }

    if (name === "pain_active") {
      const out = await tail(PAIN_LOG, args.window_hours || 24);
      return {
        content: [{ type: "text", text: JSON.stringify(out, null, 2) }],
      };
    }

    if (name === "intuition_for_pattern") {
      const entries = await readIntuitionDb();
      const matches = intuitionMatch(args.text || "", entries);
      const out = matches.length
        ? matches
        : {
            note: "no strong matches in intuition db",
            db_size: entries.length,
          };
      return {
        content: [{ type: "text", text: JSON.stringify(out, null, 2) }],
      };
    }

    if (name === "vision_latest") {
      const v = await latestVisionReport();
      const out = v || {
        note: "no vision reports found at /tmp/video-intelligence/",
      };
      return {
        content: [{ type: "text", text: JSON.stringify(out, null, 2) }],
      };
    }

    if (name === "status") {
      const [smell, pain, db, vision] = await Promise.all([
        tail(SMELL_LOG, 24),
        tail(PAIN_LOG, 24),
        readIntuitionDb(),
        latestVisionReport(),
      ]);
      const summary = {
        smell: { count_24h: smell.entries.length, note: smell.note },
        pain: { count_24h: pain.entries.length, note: pain.note },
        intuition: { db_size: db.length },
        vision: vision
          ? {
              latest_path: vision.path,
              has_report: !vision.report.includes("vision still processing"),
            }
          : { none: true },
        alert_level:
          pain.entries.length > 5
            ? "high"
            : pain.entries.length > 0
              ? "medium"
              : smell.entries.length > 10
                ? "low"
                : "idle",
      };
      return {
        content: [{ type: "text", text: JSON.stringify(summary, null, 2) }],
      };
    }

    return {
      content: [{ type: "text", text: `unknown tool: ${name}` }],
      isError: true,
    };
  } catch (err) {
    return {
      content: [{ type: "text", text: `error: ${err.message}` }],
      isError: true,
    };
  }
});

// ---------- run ----------

const transport = new StdioServerTransport();
await server.connect(transport);
