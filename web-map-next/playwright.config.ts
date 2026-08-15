import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.SURGE_E2E_BASE_URL ?? 'http://localhost:5174';

export default defineConfig({
  testDir: './src/test/e2e',
  // A real optimisation runs synchronously inside the POST, and on the reference dataset that is
  // tens of seconds. A short timeout here fails the run rather than the product.
  timeout: 180_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }]
});
