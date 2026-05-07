// axe-playwright-starter.spec.ts
//
// Reference pattern for /review-stack L4 accessibility audit.
// Copy into any Next.js + Playwright project as `tests/a11y/smoke.spec.ts`
// then either:
//   - tag specs with @a11y and run: `npx playwright test --grep @a11y`
//   - or define a dedicated Playwright project named "a11y"
//     in playwright.config.ts and run: `npx playwright test --project=a11y`
//
// Prereqs: `npm i -D @axe-core/playwright`
// Docs:    https://www.npmjs.com/package/@axe-core/playwright
//
// The /review-stack --audit gate looks for findings in `axe.violations[]` with
// `impact` of "critical" | "serious" (blocking at `--gate hard`),
// "moderate" (warn), "minor" (info, only at --deep).
//
// Customize ROUTES for your site. Keep the list tight (4-7 key routes) — axe
// takes ~1-2s per route with a warm page.

import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const BASE = process.env.E2E_BASE_URL ?? 'http://localhost:3000';

const ROUTES: { name: string; path: string }[] = [
  { name: 'home', path: '/' },
];

// WCAG 2.1 AA is the default bar. Extend tags only if you target AAA.
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'];

for (const route of ROUTES) {
  test(`@a11y ${route.name} has no critical/serious violations`, async ({ page }) => {
    await page.goto(`${BASE}${route.path}`, { waitUntil: 'networkidle' });

    const results = await new AxeBuilder({ page })
      .withTags(WCAG_TAGS)
      // Exclude third-party widgets we don't control. Keep this list minimal.
      // .exclude('iframe[title="reCAPTCHA"]')
      .analyze();

    // Blocking set: critical + serious. Moderate/minor are warnings in the
    // /review-stack gate but don't fail the Playwright test itself — the
    // gate re-evaluates from the JSON.
    const blocking = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious',
    );

    if (blocking.length > 0) {
      // Log a compact summary so CI output surfaces the issue without noise.
      console.log(`\n[a11y] ${route.name} violations:`);
      for (const v of blocking) {
        console.log(`  - [${v.impact}] ${v.id}: ${v.help}`);
        console.log(`    nodes: ${v.nodes.length}, first: ${v.nodes[0]?.target?.join(' ')}`);
        console.log(`    wcag:  ${v.tags.filter((t) => t.startsWith('wcag')).join(', ')}`);
      }
    }

    expect(blocking, `${blocking.length} critical/serious a11y violations on ${route.path}`).toEqual([]);
  });
}
