import { test, expect } from "@playwright/test";

// Non-a11y smoke: exercise routing + DOM. Uses playwright.config baseURL (audit static server).

test.describe("smoke", () => {
  test("home loads and shows expected heading", async ({ page }) => {
    const res = await page.goto("/");
    expect(res?.ok()).toBeTruthy();
    await expect(page.getByRole("heading", { level: 1 })).toContainText(
      "Hermes agents monorepo",
    );
  });

  test("home has main landmark", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("main")).toBeVisible();
  });
});
