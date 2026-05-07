// playwright.config.ts — scaffolded by /audit-setup.
// Edit freely; the skill never overwrites an existing config.
import { defineConfig } from "@playwright/test";

/** Fixed port avoids collisions with common dev servers on :3000 (Lighthouse / Playwright / run-baseline must match). */
const AUDIT_STATIC_PORT = process.env.AUDIT_STATIC_PORT ?? "3099";
const staticOrigin = `http://127.0.0.1:${AUDIT_STATIC_PORT}`;

export default defineConfig({
  testDir: "tests",
  webServer: {
    command: `npm run build && npx --yes serve@14 dist --listen ${AUDIT_STATIC_PORT}`,
    url: staticOrigin,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  use: {
    baseURL: process.env.E2E_BASE_URL ?? staticOrigin,
  },
  projects: [
    {
      name: "smoke",
      testMatch: /tests\/smoke\/.*\.spec\.ts/,
    },
    {
      name: "a11y",
      testMatch: /tests\/a11y\/.*\.spec\.ts/,
      grep: /@a11y/,
    },
  ],
});
