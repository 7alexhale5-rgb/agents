#!/usr/bin/env node
/**
 * Writes a minimal static site to dist/ so `npm start` + Lighthouse can run
 * at repo root (Python / Hermes monorepo has no Next.js app here).
 */
import fs from "node:fs";
import path from "node:path";

const dir = path.join(process.cwd(), "dist");
fs.mkdirSync(dir, { recursive: true });
const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Hermes agents monorepo</title>
</head>
<body>
  <main>
    <h1>Hermes agents monorepo</h1>
    <p>Static placeholder for Lighthouse baseline. Real UIs live in product repos.</p>
  </main>
</body>
</html>
`;
fs.writeFileSync(path.join(dir, "index.html"), html, "utf8");
console.log("wrote dist/index.html");
