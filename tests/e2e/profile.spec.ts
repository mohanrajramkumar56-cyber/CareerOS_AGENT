// spec: specs/plan.md#4-profile-page
// seed: seed.spec.ts
//
// Profile page uses static placeholder data (auth UI ships in Phase 6),
// so all assertions target the placeholder content.

import { test, expect } from "@playwright/test";

test.describe("Profile Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/profile");
    await page.waitForLoadState("domcontentloaded");
  });

  // ── 4.1 ────────────────────────────────────────────────────────────────────

  test("shows profile heading with placeholder name and headline", async ({ page }) => {
    // H1 contains the placeholder name
    await expect(page.getByRole("heading", { level: 1, name: "Your Name" })).toBeVisible();

    // Placeholder headline in the header area
    await expect(page.getByText("Your Professional Headline")).toBeVisible();
  });

  // ── 4.2 ────────────────────────────────────────────────────────────────────

  test("Identity section renders with Phase 1 badge and fields", async ({ page }) => {
    // Section heading
    await expect(page.getByRole("heading", { name: "Identity" })).toBeVisible();

    // Phase 1 badge
    await expect(page.getByText("Phase 1")).toBeVisible();

    // Field labels (inside a dl element)
    for (const label of ["Location", "Experience", "Work Style", "Authorization"]) {
      await expect(page.getByText(label, { exact: true })).toBeVisible();
    }
  });

  // ── 4.3 ────────────────────────────────────────────────────────────────────

  test("Skills section shows 5 skills with evidence badges", async ({ page }) => {
    // Section heading
    await expect(page.getByRole("heading", { name: "Skills" })).toBeVisible();

    // Badge showing skill count
    await expect(page.getByText("5 skills")).toBeVisible();

    // Each placeholder skill visible
    for (const skill of ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"]) {
      await expect(page.getByText(skill, { exact: true })).toBeVisible();
    }

    // Evidence badge labels visible
    for (const strength of ["verified", "strong", "moderate", "weak", "unknown"]) {
      await expect(
        page.getByLabel(`Evidence strength: ${strength}`).first()
      ).toBeVisible();
    }
  });

  // ── 4.4 ────────────────────────────────────────────────────────────────────

  test("Evidence Graph section renders 3 facts with truth policy note", async ({ page }) => {
    // Section heading
    await expect(page.getByRole("heading", { name: "Evidence Graph" })).toBeVisible();

    // Badge showing fact count
    await expect(page.getByText("3 facts")).toBeVisible();

    // Fact list
    const factList = page.getByRole("list", { name: "Candidate facts" });
    await expect(factList).toBeVisible();
    await expect(factList.getByRole("listitem")).toHaveCount(3);

    // Fact category labels present
    for (const cat of ["experience", "certification", "skill"]) {
      await expect(factList.getByText(cat, { exact: true })).toBeVisible();
    }

    // Truth policy warning box
    await expect(page.getByText("Truth policy:")).toBeVisible();
  });

  // ── 4.5 ────────────────────────────────────────────────────────────────────

  test("Edit Profile button is visible and keyboard-accessible", async ({ page }) => {
    const btn = page.getByRole("button", { name: "Edit candidate profile" });
    await expect(btn).toBeVisible();
    await expect(btn).toBeEnabled();

    // Keyboard focus
    await btn.focus();
    await expect(btn).toBeFocused();
  });

  // ── 4.6 ────────────────────────────────────────────────────────────────────

  test("API endpoint note is shown at page bottom", async ({ page }) => {
    await expect(
      page.getByText(/GET \/api\/v1\/candidates\/profile/)
    ).toBeVisible();
  });
});
