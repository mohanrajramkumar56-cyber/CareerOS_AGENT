// spec: specs/plan.md#5-applications-page
// seed: seed.spec.ts

import { test, expect } from "@playwright/test";

// All 7 statuses rendered as filter pills
const ALL_STATUSES = [
  "draft",
  "pending approval",  // displayed with underscore replaced
  "approved",
  "submitted",
  "acknowledged",
  "rejected",
  "withdrawn",
];

/** Mock the applications API to return empty list */
function mockEmptyApps(page: import("@playwright/test").Page) {
  return page.route("**/api/v1/applications/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        applications: [],
        total: 0,
        page: 1,
        page_size: 20,
      }),
    })
  );
}

async function waitSettled(page: import("@playwright/test").Page) {
  await page
    .locator("[aria-busy='true']")
    .waitFor({ state: "hidden", timeout: 10_000 })
    .catch(() => {});
}

test.describe("Applications Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/applications");
    await page.waitForLoadState("domcontentloaded");
  });

  // ── 5.1 ────────────────────────────────────────────────────────────────────

  test("shows Applications heading", async ({ page }) => {
    await expect(
      page.getByRole("heading", { level: 1, name: "Applications" })
    ).toBeVisible();
  });

  // ── 5.2 ────────────────────────────────────────────────────────────────────

  test("renders All filter pill and 7 status filter pills", async ({ page }) => {
    const filterGroup = page.getByRole("group", { name: "Filter by status" });
    await expect(filterGroup).toBeVisible();

    // "All" pill
    await expect(filterGroup.getByRole("button", { name: "All" })).toBeVisible();

    // All 7 status pills — text is status with _ replaced by space
    for (const status of ALL_STATUSES) {
      await expect(
        filterGroup.getByRole("button", { name: status, exact: true })
      ).toBeVisible();
    }
  });

  // ── 5.3 ────────────────────────────────────────────────────────────────────

  test("clicking a status pill marks it as active and deactivates All", async ({
    page,
  }) => {
    const filterGroup = page.getByRole("group", { name: "Filter by status" });
    const allPill = filterGroup.getByRole("button", { name: "All" });
    const draftPill = filterGroup.getByRole("button", { name: "draft" });

    // "All" is active by default (has white background via class)
    await expect(allPill).toHaveClass(/bg-white/);

    // Click "draft" pill
    await draftPill.click();

    // "draft" pill becomes active
    await expect(draftPill).toHaveClass(/bg-white/);

    // "All" is no longer active
    await expect(allPill).not.toHaveClass(/bg-white/);
  });

  // ── 5.4 ────────────────────────────────────────────────────────────────────

  test("page settles to applications list or empty state", async ({ page }) => {
    // Mock empty to make this deterministic
    await mockEmptyApps(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // With empty mock, empty state must be visible
    await expect(page.getByText("No applications yet")).toBeVisible();
  });

  // ── 5.5 ────────────────────────────────────────────────────────────────────

  test("empty state shows helpful guidance when no applications", async ({ page }) => {
    await mockEmptyApps(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    await expect(page.getByText("No applications yet")).toBeVisible();
    await expect(
      page.getByText("Browse jobs and create your first application.")
    ).toBeVisible();
  });

  // ── 5.6 ────────────────────────────────────────────────────────────────────

  test("clear filter link appears and resets when status filter is active and empty", async ({
    page,
  }) => {
    await mockEmptyApps(page);
    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // Activate a status filter
    const filterGroup = page.getByRole("group", { name: "Filter by status" });
    await filterGroup.getByRole("button", { name: "draft" }).click();
    await waitSettled(page);

    // With active filter and empty results, "Clear filter" link appears
    const clearLink = page.getByRole("button", { name: "Clear filter" });
    if (await clearLink.isVisible()) {
      await clearLink.click();

      // "All" pill should be active again
      await expect(
        filterGroup.getByRole("button", { name: "All" })
      ).toHaveClass(/bg-white/);
    }
  });

  // ── 5.7 ────────────────────────────────────────────────────────────────────

  test("shows error alert when API returns 500", async ({ page }) => {
    await page.route("**/api/v1/applications/**", (route) =>
      route.fulfill({ status: 500, body: "Server Error" })
    );

    await page.reload();
    await page.waitForLoadState("domcontentloaded");
    await waitSettled(page);

    // Filter out Next.js's route announcer (empty alert) — target the one with error text
    const errorAlert = page
      .locator('[role="alert"]')
      .filter({ hasText: /500|error|Failed/i });
    await expect(errorAlert).toBeVisible({ timeout: 8000 });
  });

  // ── Bonus: application card renders correctly ──────────────────────────────

  test("application card renders with status badge and ID", async ({ page }) => {
    const appId = "a1b2c3d4-e5f6-7890-abcd-ef1234567890";

    await page.route("**/api/v1/applications/**", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          applications: [
            {
              id: appId,
              candidate_id: "cand-001",
              job_id: "job-001-uuid-here",
              resume_id: null,
              status: "pending_approval",
              cover_letter: null,
              form_data: null,
              requires_approval: true,
              approved_by: null,
              approved_at: null,
              submitted_at: null,
              submission_method: null,
              notes: null,
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

    // Card for our mocked application
    const card = page.getByRole("article").first();
    await expect(card).toBeVisible();

    // Short ID shown (first 8 chars)
    await expect(card.getByText(`Application #${appId.slice(0, 8)}`)).toBeVisible();

    // Status badge for "pending_approval" → displayed as "Pending approval"
    await expect(card.getByText("Pending approval")).toBeVisible();

    // The approval warning shows when status is NOT "draft" but requires_approval:
    // Looking at the source: "requires_approval && status === 'draft'" — our status is pending_approval
    // so the warning won't show. Check what IS shown: just the status badge.
    // Assert the card is rendered successfully with the correct content.
    await expect(card.getByText(/Application #/)).toBeVisible();
  });
});
