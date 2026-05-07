#!/usr/bin/env node
// summarize-lighthouse.mjs
// Reads raw Lighthouse JSONs (multiple runs per route), computes per-route
// median scores, writes one canonical <slug>.report.json per route, and emits
// a SUMMARY.md table.
//
// Usage:
//   node summarize-lighthouse.mjs --raw-dir <path> --out-dir <path>

import { readdirSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, basename } from 'node:path';

const args = Object.fromEntries(
  process.argv.slice(2).reduce((a, v, i, arr) => (i % 2 === 0 ? [...a, [v.replace(/^--/, ''), arr[i + 1]]] : a), []),
);
const RAW_DIR = args['raw-dir'];
const OUT_DIR = args['out-dir'];
if (!RAW_DIR || !OUT_DIR) {
  console.error('usage: --raw-dir <path> --out-dir <path>');
  process.exit(2);
}
mkdirSync(OUT_DIR, { recursive: true });

// Group raw files by slug: foo.1.json, foo.2.json, foo.3.json → slug "foo"
const grouped = {};
for (const f of readdirSync(RAW_DIR)) {
  const m = f.match(/^(.+)\.(\d+)\.json$/);
  if (!m) continue;
  grouped[m[1]] ??= [];
  grouped[m[1]].push(join(RAW_DIR, f));
}

const median = (arr) => {
  const sorted = [...arr].filter((n) => n != null).sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
};

const rows = [];
for (const slug of Object.keys(grouped).sort()) {
  const runs = grouped[slug].map((p) => JSON.parse(readFileSync(p, 'utf8')));
  if (!runs.length) continue;
  // Pick the run whose performance score is the median — use its full JSON as
  // the canonical report for that route.
  const perfScores = runs.map((r) => r.categories?.performance?.score ?? 0);
  const medPerf = median(perfScores);
  const medianRun = runs.find((r) => r.categories?.performance?.score === medPerf) ?? runs[0];
  writeFileSync(join(OUT_DIR, `${slug}.report.json`), JSON.stringify(medianRun));

  const cats = medianRun.categories;
  const audits = medianRun.audits;
  rows.push({
    slug,
    perf: cats.performance?.score,
    a11y: cats.accessibility?.score,
    bp: cats['best-practices']?.score,
    seo: cats.seo?.score,
    lcp: audits['largest-contentful-paint']?.numericValue,
    cls: audits['cumulative-layout-shift']?.numericValue,
    tbt: audits['total-blocking-time']?.numericValue,
    fcp: audits['first-contentful-paint']?.numericValue,
  });
}

const pct = (n) => (n == null ? '—' : String(Math.round(n * 100)));
const ms = (v) => (v == null ? '—' : `${(v / 1000).toFixed(2)}s`);

const md = [
  `# Lighthouse baseline — ${new Date().toISOString().slice(0, 10)}`,
  '',
  `Mobile preset · 3×-median · ${rows.length} routes`,
  '',
  '| Route | Perf | A11y | BP | SEO | LCP | FCP | CLS | TBT |',
  '|---|---|---|---|---|---|---|---|---|',
  ...rows.map(
    (r) =>
      `| \`${r.slug}\` | ${pct(r.perf)} | ${pct(r.a11y)} | ${pct(r.bp)} | ${pct(r.seo)} | ${ms(r.lcp)} | ${ms(r.fcp)} | ${(r.cls ?? 0).toFixed(3)} | ${ms(r.tbt)} |`,
  ),
  '',
  '_Perf / A11y / BP / SEO scores: 0–100. Hard floor per /review-stack: perf ≥80, a11y ≥90, bp ≥90, seo ≥85. Targets: CLS <0.1, LCP <4s._',
  '',
].join('\n');

writeFileSync(join(OUT_DIR, 'SUMMARY.md'), md);
console.log(`summarize-lighthouse: ${rows.length} routes → ${OUT_DIR}/SUMMARY.md`);
