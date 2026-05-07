// playwright.config.ts — scaffolded by /audit-setup.
// Edit freely; the skill never overwrites an existing config.
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "tests",
  webServer: {
    // Static placeholder from scripts/audit-devserver-build.mjs (repo has no Next.js app)
    command: "npm run build && npx --yes serve@14 dist -l 3000",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
  },
  projects: [
    { name: "a11y", testMatch: /.*\.spec\.ts/, grep: /@a11y/ },
    { name: "smoke", testMatch: /.*\.spec\.ts/, grepInvert: /@a11y/ },
  ],
});
