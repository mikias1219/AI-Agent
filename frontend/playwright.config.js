import { defineConfig } from '@playwright/test';
function quote(value) {
  return `'${value.replaceAll("'", "'\\''")}'`;
}
export default defineConfig({
  testDir: './tests/e2e',
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:8011',
    viewport: { width: 1440, height: 1000 },
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE, args: ['--no-sandbox'] }
      : {},
    trace: 'retain-on-failure',
  },
  webServer: {
    command: `${quote(process.env.BACKEND_PYTHON || 'python')} tests/fixtures/serve_backend.py`,
    url: 'http://127.0.0.1:8011/api/auth',
    reuseExistingServer: false,
    timeout: 30000,
  },
});
