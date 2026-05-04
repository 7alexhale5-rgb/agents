#!/usr/bin/env node
/**
 * Smoke test for the 4d-senses MCP server.
 * Spawns the server, sends a list-tools request and a call-tool request.
 */

import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const serverPath = join(__dirname, "index.js");

const proc = spawn("node", [serverPath], {
  stdio: ["pipe", "pipe", "inherit"],
});

let buf = "";
proc.stdout.on("data", (chunk) => {
  buf += chunk.toString();
  const lines = buf.split("\n");
  buf = lines.pop() || "";
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const msg = JSON.parse(line);
      console.log("← ", JSON.stringify(msg, null, 2).slice(0, 600));
    } catch {
      console.log("← (raw)", line);
    }
  }
});

function send(req) {
  console.log("→", JSON.stringify(req));
  proc.stdin.write(JSON.stringify(req) + "\n");
}

setTimeout(() => {
  send({ jsonrpc: "2.0", id: 1, method: "tools/list", params: {} });
}, 200);

setTimeout(() => {
  send({
    jsonrpc: "2.0",
    id: 2,
    method: "tools/call",
    params: { name: "status", arguments: {} },
  });
}, 600);

setTimeout(() => {
  proc.kill();
  process.exit(0);
}, 1500);
