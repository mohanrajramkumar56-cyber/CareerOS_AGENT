import { defineConfig, devices } from "@playwright/test";

/**
 * CareerOS — Playwright E2E Configuration
 *
 * Runs against the Next.js dev server at http://localhost:3000.
 * Set PLAYWRIGHT_BASE_URL env var to target a different environment.
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],

  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    // Give pages time to make API calls — API may be slow/unavailable
    actionTimeout: 10_000,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "firefox",
      use: { ...devices["Desktop Firefox"] },
    },
  ],

  // Start Next.js dev server automatically when running tests locally
  webServer: {
    command: "npm run dev --prefix apps/web",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
