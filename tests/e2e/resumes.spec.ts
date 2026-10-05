// spec: specs/plan.md#6-resumes-page
// seed: seed.spec.ts

import { test, expect } from "@playwright/test";

async function waitSettled(page: import("@playwright/test").Page) {
  await page
    .locator("[aria-busy='true']")
    .waitFor({ state: "hidden", timeout: 10_000 })
    .catch(() => {});
}

test.describe("Resumes Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/resumes");
    await page.waitForLoadState("domcontentloaded");
  });

  // ── 6.1 ────────────────────────────────────────────────────────────────────

  test("shows Resumes heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { level: 1, name: "Resumes" })
    ).toBeVisible();
  });

  // ── 6.2 ────────────────────────────────────────────────────────────────────

  test("shows loading state then settles to list or empty state", async ({ page }) => {
    // Mock empty to make deterministic
    await page.route("**/api/v1/resumes/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ resumes: [], total: 0, page: 1, page_size: 20 }),
      })
    );
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    await expect(page.getByText("No resumes yet")).toBeVisible();
  });

  // ── 6.3 ────────────────────────────────────────────────────────────────────

  test("empty state shows API generation hint", async ({ page }) => {
    // Force empty response
    await page.route("**/api/v1/resumes/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ resumes: [], total: 0, page: 1, page_size: 20 }),
      })
    );

    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    await expect(page.getByText("No resumes yet")).toBeVisible();

    // API hint appears in two places: header area + empty state paragraph
    // Use .first() to avoid strict mode violation
    const apiHint = page.getByText(/POST \/api\/v1\/resumes\//).first();
    await expect(apiHint).toBeVisible();

    // Sample JSON payload hint
    await expect(page.getByText(/"template"/)).toBeVisible();
  });

  // ── 6.4 ────────────────────────────────────────────────────────────────────

  test("resume card shows title, template badge and Truth Policy badge", async ({
    page,
  }) => {
    const resumeId = "res-001-uuid-1234-5678-9abc";

    // Mock a resume in the response
    await page.route("**/api/v1/resumes/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          resumes: [
            {
              id: resumeId,
              candidate_id: "cand-001",
              job_id: null,
              title: "Software Engineer Resume",
              template: "technical",
              is_tailored: false,
              truth_policy_enforced: true,
              facts_excluded_count: 2,
              version: 1,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
      })
    );

    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // Card should be visible
    const card = page.getByRole("article").first();
    await expect(card).toBeVisible();

    // Title
    await expect(card.getByText("Software Engineer Resume")).toBeVisible();

    // Template badge
    await expect(card.getByText("technical")).toBeVisible();

    // Truth Policy badge
    await expect(card.getByText("Truth Policy ✓")).toBeVisible();

    // Facts excluded badge (2 facts excluded)
    await expect(card.getByText("2 facts excluded")).toBeVisible();

    // Markdown link
    await expect(
      card.getByRole("link", { name: /View markdown for Software Engineer Resume/ })
    ).toBeVisible();
  });

  // ── 6.5 ────────────────────────────────────────────────────────────────────

  test("API endpoint note is visible in header area", async ({ page }) => {
    // The API note appears in the page header — use first() since it may repeat in empty state
    const apiNote = page.getByText(/POST \/api\/v1\/resumes\//).first();
    await expect(apiNote).toBeVisible();
  });

  // ── 6.6 ────────────────────────────────────────────────────────────────────

  test("shows error alert when API returns 500", async ({ page }) => {
    await page.route("**/api/v1/resumes/**", (route) =>
      route.fulfill({ status: 500, body: "Server Error" })
    );

    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // Filter out Next.js's empty route announcer alert
    const errorAlert = page
      .locator('[role="alert"]')
      .filter({ hasText: /500|error|Failed/i });
    await expect(errorAlert).toBeVisible({ timeout: 8000 });
  });

  // ── 6.7 — Template color variants ─────────────────────────────────────────

  test("tailored resume shows Tailored badge", async ({ page }) => {
    await page.route("**/api/v1/resumes/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          resumes: [
            {
              id: "res-tailored-001",
              candidate_id: "cand-001",
              job_id: "job-001",
              title: "Tailored Resume for Acme",
              template: "standard",
              is_tailored: true,
              truth_policy_enforced: true,
              facts_excluded_count: 0,
              version: 2,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
      })
    );

    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    const card = page.getByRole("article").first();
    // The "Tailored" badge text — use exact: true to get the badge, not the title
    await expect(card.getByText("Tailored", { exact: true })).toBeVisible();
    await expect(card.getByText("standard")).toBeVisible();
  });

  // ── Sidebar navigation ─────────────────────────────────────────────────────

  test("sidebar has Resumes link that is present", async ({ page }) => {
    const sidebar = page.getByRole("complementary", { name: "Main navigation" });
    await expect(sidebar.getByRole("link", { name: "Resumes" })).toBeVisible();
  });
});
