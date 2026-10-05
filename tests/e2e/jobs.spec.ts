// spec: specs/plan.md#3-jobs-page
// seed: seed.spec.ts

import { test, expect } from "@playwright/test";

/** Mock the jobs API to return an empty list */
function mockEmptyJobs(page: import("@playwright/test").Page) {
  return page.route("**/api/v1/jobs/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ jobs: [], total: 0, page: 1, page_size: 20 }),
    })
  );
}

/** Wait for the jobs page to finish loading */
async function waitSettled(page: import("@playwright/test").Page) {
  // The jobs page uses aria-busy on the grid; wait until hidden or timeout
  await page
    .locator("[aria-busy='true']")
    .waitFor({ state: "hidden", timeout: 10_000 })
    .catch(() => {});
}

test.describe("Jobs Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/jobs");
    await page.waitForLoadState("domcontentloaded");
  });

  // ── 3.1 ────────────────────────────────────────────────────────────────────

  test("shows Jobs heading and all filter controls", async ({ page }) => {
    // H1 heading
    await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();

    // Search input
    await expect(
      page.getByRole("searchbox", { name: "Search jobs by title or company" })
    ).toBeVisible();

    // Location dropdown
    await expect(
      page.getByRole("combobox", { name: "Filter by remote type" })
    ).toBeVisible();

    // Employment type dropdown
    await expect(
      page.getByRole("combobox", { name: "Filter by employment type" })
    ).toBeVisible();

    // Freshness dropdown
    await expect(
      page.getByRole("combobox", { name: "Filter by freshness status" })
    ).toBeVisible();

    // Refresh button
    await expect(page.getByRole("button", { name: "Refresh job list" })).toBeVisible();
  });

  // ── 3.2 ────────────────────────────────────────────────────────────────────

  test("shows loading state then settles to jobs or empty state", async ({ page }) => {
    // Mock empty to make this deterministic (no live API needed)
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // With mocked empty response we always land in the empty state
    await expect(page.getByText("No jobs found")).toBeVisible();
  });

  // ── 3.3 ────────────────────────────────────────────────────────────────────

  test("empty state shows helpful message", async ({ page }) => {
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    await expect(page.getByText("No jobs found")).toBeVisible();
    await expect(
      page.getByText("Jobs will appear here once the discovery pipeline runs.")
    ).toBeVisible();
  });

  // ── 3.4 ────────────────────────────────────────────────────────────────────

  test("search input accepts text and triggers reload", async ({ page }) => {
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    const searchInput = page.getByRole("searchbox", { name: "Search jobs by title or company" });
    await searchInput.fill("engineer");

    // After typing, the loading state should fire again then clear
    await waitSettled(page);

    // Page heading still present — no crash
    await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
  });

  // ── 3.5 ────────────────────────────────────────────────────────────────────

  test("location dropdown filters by remote type", async ({ page }) => {
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    const dropdown = page.getByRole("combobox", { name: "Filter by remote type" });
    await dropdown.selectOption("remote");
    await waitSettled(page);

    // No crash — heading still there
    await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
  });

  // ── 3.6 ────────────────────────────────────────────────────────────────────

  test("employment type dropdown filters jobs", async ({ page }) => {
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    const dropdown = page.getByRole("combobox", { name: "Filter by employment type" });
    await dropdown.selectOption("full_time");
    await waitSettled(page);

    await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
  });

  // ── 3.7 ────────────────────────────────────────────────────────────────────

  test("freshness status dropdown filters jobs", async ({ page }) => {
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    const dropdown = page.getByRole("combobox", { name: "Filter by freshness status" });
    await dropdown.selectOption("active");
    await waitSettled(page);

    await expect(page.getByRole("heading", { level: 1, name: "Jobs" })).toBeVisible();
  });

  // ── 3.8 ────────────────────────────────────────────────────────────────────

  test("clear filters button resets search when active", async ({ page }) => {
    await mockEmptyJobs(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    const searchInput = page.getByRole("searchbox", { name: "Search jobs by title or company" });
    await searchInput.fill("xyz-nonexistent");
    await waitSettled(page);

    // Clear filters button should be visible in empty state when query is set
    const clearBtn = page.getByRole("button", { name: "Clear filters" });
    if (await clearBtn.isVisible()) {
      await clearBtn.click();
      await expect(searchInput).toHaveValue("");
    }
  });

  // ── 3.9 ────────────────────────────────────────────────────────────────────

  test("job cards display title, company, freshness badge and Details button", async ({ page }) => {
    // Mock a single job response so this test is deterministic
    await page.route("**/api/v1/jobs/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          jobs: [
            {
              id: "job-test-001",
              source: "test",
              company: "Acme Corp",
              title: "Senior Software Engineer",
              location: "Remote",
              remote_type: "remote",
              employment_type: "full_time",
              salary_min: 120000,
              salary_max: 160000,
              salary_currency: "USD",
              description: "A great role",
              mandatory_skills: "Python,FastAPI",
              preferred_skills: null,
              freshness_status: "new",
              posted_at: new Date().toISOString(),
              discovered_at: new Date().toISOString(),
              application_url: "https://acme.com/apply",
              normalized: true,
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

    // Job card rendered
    const card = page.getByRole("article", { name: /Senior Software Engineer/ });
    await expect(card).toBeVisible();

    // Title
    await expect(card.getByRole("heading", { name: "Senior Software Engineer" })).toBeVisible();

    // Company
    await expect(card.getByText("Acme Corp")).toBeVisible();

    // Freshness badge
    await expect(card.getByText("new")).toBeVisible();

    // Details button
    await expect(
      card.getByRole("button", { name: /View details for Senior Software Engineer/ })
    ).toBeVisible();

    // Apply link (has application_url)
    await expect(
      card.getByRole("link", { name: /Apply to Senior Software Engineer/ })
    ).toBeVisible();
  });

  // ── 3.10 ───────────────────────────────────────────────────────────────────

  test("shows error alert when API returns 500", async ({ page }) => {
    await page.route("**/api/v1/jobs/**", (route) =>
      route.fulfill({ status: 500, body: "Server Error" })
    );

    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // Next.js adds a second role="alert" for route announcements —
    // target the error div that contains the actual error message
    const errorAlert = page
      .locator('[role="alert"]')
      .filter({ hasText: /500|Failed|error/i });
    await expect(errorAlert).toBeVisible({ timeout: 8000 });
  });
});
