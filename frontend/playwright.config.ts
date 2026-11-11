import { defineConfig, devices } from "@playwright/test";

const API_PORT = 8011; // tests/fixtures/serve_backend.py
const WEB_PORT = 3100;
const API_URL = `http://127.0.0.1:${API_PORT}`;
const WEB_URL = `http://127.0.0.1:${WEB_PORT}`;
const python = process.env.E2E_PYTHON || "python";

// Full-stack smoke: real FastAPI app (fake model provider, temp SQLite, mocked Telegram HTTP)
// behind a real Next.js production build that proxies /api → the fixture backend.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0, // single-owner account is created in-test, so a retry would hit "registration closed"
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    baseURL: WEB_URL,
    trace: "retain-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `${python} tests/fixtures/serve_backend.py`,
      url: `${API_URL}/api/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
    },
    {
      // Rewrites are baked at build time, so the proxy target must be set for the build too.
      command: `npm run build && npx next start --port ${WEB_PORT}`,
      url: `${WEB_URL}/login`,
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
      env: {
        PERSONAL_AGENT_BACKEND_URL: API_URL,
        NEXT_PUBLIC_API_BASE_URL: "",
      },
    },
  ],
});
