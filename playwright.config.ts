import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for CreatorIQ Stabilization Testing.
 * Enforces high-reliability, deterministic E2E assertions.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: 1, // Determinism requirement
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    viewport: { width: 1280, height: 720 },
    video: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      command: 'npm run dev',
      port: 5173,
      reuseExistingServer: !process.env.CI,
      cwd: './frontend'
    },
    {
      command: 'python -m uvicorn app.main:app --port 8000',
      port: 8000,
      reuseExistingServer: !process.env.CI,
      cwd: './backend',
      env: {
        TEST_MODE: 'true',
        MONGODB_DB_NAME: 'creatoriq_test'
      }
    }
  ],
});
