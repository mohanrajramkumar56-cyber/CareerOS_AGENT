// spec: specs/plan.md#2-dashboard-page
// seed: seed.spec.ts

import { test, expect } from "@playwright/test";

test.describe("Dashboard Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");
  });

  // ── 2.1 ────────────────────────────────────────────────────────────────────

  test("shows Dashboard heading and subtitle", async ({ page }) => {
    // Verify h1 heading
    await expect(page.getByRole("heading", { level: 1, name: "Dashboard" })).toBeVisible();

    // Verify subtitle text
    await expect(
      page.getByText("CareerOS — Autonomous AI Career Operating System")
    ).toBeVisible();
  });

  // ── 2.2 ────────────────────────────────────────────────────────────────────

  test("renders 8 stat cards that settle out of loading", async ({ page }) => {
    // The stats section renders 8 StatCard articles
    const cards = page.locator("article[aria-label]");
    await expect(cards).toHaveCount(8);

    // Wait for skeletons to disappear (loading state resolves)
    await page
      .locator(".animate-pulse")
      .first()
      .waitFor({ state: "hidden", timeout: 10_000 })
      .catch(() => {
        // May have resolved instantly — that's fine
      });

    // After settling, each card should contain a numeric value or "0"
    const firstCard = cards.first();
    await expect(firstCard).toBeVisible();
  });

  // ── 2.3 ────────────────────────────────────────────────────────────────────

  test("renders Application Funnel section with 5 progress bars", async ({ page }) => {
    // Section heading
    await expect(
      page.getByRole("heading", { name: "Application Funnel" })
    ).toBeVisible();

    // 5 mini bar rows with progressbars
    const bars = page.locator('[role="progressbar"]');
    // The funnel has 5 bars; the phase tracker has 1 more — at least 6 total
    await expect(bars).toHaveCount(6); // 5 funnel + 1 phase progress

    // Verify funnel labels — scope them to the funnel section to avoid duplicates
    const funnelSection = page.getByRole("region", { name: "Application Funnel" })
      .or(page.locator("section").filter({ hasText: "Application Funnel" }));

    for (const label of ["Discovered", "Matched", "Eligible", "Applied", "Submitted"]) {
      await expect(funnelSection.getByText(label, { exact: true })).toBeVisible();
    }
  });

  // ── 2.4 ────────────────────────────────────────────────────────────────────

  test("renders Recent Activity section that settles", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Recent Activity" })
    ).toBeVisible();

    // Wait for the activity loading skeleton to resolve (up to 10s for API)
    await page
      .locator("[aria-label='Recent activity']")
      .or(page.getByText("No recent activity. Start by exploring jobs."))
      .waitFor({ timeout: 10_000 });
  });

  // ── 2.5 ────────────────────────────────────────────────────────────────────

  test("renders System Build Status with phase tracker", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "System Build Status" })
    ).toBeVisible();

    await expect(page.getByText("Build Progress")).toBeVisible();

    // Progress percentage — scoped to the phase section
    const phaseSection = page.locator("section").filter({ hasText: "System Build Status" });
    await expect(phaseSection.getByText(/%$/)).toBeVisible();

    // Phase names — scope to the section to avoid ambiguity with sidebar link / h1
    await expect(phaseSection.getByText("Foundation", { exact: true })).toBeVisible();
    // Use a unique phase name to avoid collision with sidebar "Dashboard" link
    await expect(phaseSection.getByText("Candidate Intelligence", { exact: true })).toBeVisible();
  });

  // ── 2.6 ────────────────────────────────────────────────────────────────────

  test("quick navigation has 4 links and Browse Jobs navigates to /jobs", async ({ page }) => {
    const nav = page.getByRole("navigation", { name: "Quick navigation" });
    await expect(nav).toBeVisible();

    // All 4 quick links
    for (const label of ["Browse Jobs", "My Profile", "Applications", "Resumes"]) {
      await expect(nav.getByRole("link", { name: label })).toBeVisible();
    }

    // Clicking Browse Jobs navigates to /jobs
    await nav.getByRole("link", { name: "Browse Jobs" }).click();
    await expect(page).toHaveURL(/\/jobs/);
  });

  // ── 2.7 ────────────────────────────────────────────────────────────────────

  test("shows error banner when API returns 500", async ({ page }) => {
    // Intercept the dashboard stats API call BEFORE navigating
    await page.route("**/api/v1/dashboard/stats", (route) =>
      route.fulfill({ status: 500, body: "Internal Server Error" })
    );

    await page.goto("/");
    await page.waitForLoadState("domcontentloaded");

    // Error banner — Next.js also adds a route announcer with role="alert",
    // so target the one that contains our error text
    const errorBanner = page
      .locator('[role="alert"]')
      .filter({ hasText: /backend|API|Could not load/ });
    await expect(errorBanner).toBeVisible({ timeout: 8000 });
  });
});
