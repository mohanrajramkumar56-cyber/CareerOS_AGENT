// spec: specs/plan.md
// seed: seed.spec.ts
//
// Shared setup helpers and a smoke-test to verify the app is reachable.
// All E2E spec files reference this as their seed.

import { test, expect, Page } from "@playwright/test";

// ── Exported helpers ──────────────────────────────────────────────────────────

/**
 * Wait for the Next.js page to finish its initial API fetch.
 * Waits until there are no `aria-busy="true"` elements OR a timeout passes.
 */
export async function waitForPageSettled(page: Page, timeout = 8000) {
  await page
    .locator("[aria-busy='true']")
    .waitFor({ state: "hidden", timeout })
    .catch(() => {
      // Non-fatal: page may not have aria-busy at all (e.g., Profile page is static)
    });
}

/**
 * Navigate to a route and wait for the Next.js hydration to complete.
 */
export async function gotoAndWait(page: Page, path: string) {
  await page.goto(path);
  // Wait for the body to be interactive (hydration done)
  await page.waitForLoadState("domcontentloaded");
}

// ── Smoke test ────────────────────────────────────────────────────────────────

test.describe("App smoke test", () => {
  test("app is reachable and renders sidebar", async ({ page }) => {
    await gotoAndWait(page, "/");

    // Sidebar branding
    await expect(page.locator("aside")).toContainText("CareerOS");

    // Main content area exists
    await expect(page.locator("main")).toBeVisible();
  });
});
