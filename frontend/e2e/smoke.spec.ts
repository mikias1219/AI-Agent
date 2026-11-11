import { expect, test } from "@playwright/test";

// Phase 0 acceptance smoke (FND-04): register → login → chat → task, plus key routes.
// Runs against the real API with PERSONAL_AGENT_PROVIDER=fake (see playwright.config.ts).
// The backend is a single-owner app, so the steps share one account and run serially.
test.describe.configure({ mode: "serial" });

const owner = { name: "Smoke Owner", email: "owner@example.com", password: "smoke-pass-12345" };

test("login page loads and unauthenticated users are redirected to it", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();

  await page.goto("/tasks");
  await expect(page).toHaveURL(/\/login/);
});

test("register then sign in", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Name").fill(owner.name);
  await page.getByLabel("Email").fill(owner.email);
  await page.getByLabel("Password", { exact: true }).fill(owner.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/login\?registered=1/);

  await page.getByLabel("Email").fill(owner.email);
  await page.getByLabel("Password", { exact: true }).fill(owner.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/localhost:3100\/$|127\.0\.0\.1:3100\/$/);
});

test.describe("authenticated", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(owner.email);
    await page.getByLabel("Password", { exact: true }).fill(owner.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).not.toHaveURL(/\/login/);
  });

  test("chat gets a reply from the fake provider", async ({ page }) => {
    await page.goto("/chat");
    await page.getByLabel("Message your agent").fill("Hello agent");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("Hello agent")).toBeVisible();
    await expect(page.getByText("Okay.").or(page.getByText(/no local model/))).toBeVisible();
  });

  test("create a task and see the empty approvals queue", async ({ page }) => {
    await page.goto("/tasks");
    await page.getByLabel("New task").fill("Ship Phase 0");
    await page.getByRole("button", { name: "Add task" }).click();
    await expect(page.getByText("Ship Phase 0")).toBeVisible();

    await page.getByRole("tab", { name: /Approvals/ }).click();
    await expect(page.getByText("Nothing waiting")).toBeVisible();
  });

  test("key routes render", async ({ page }) => {
    for (const path of ["/", "/activity", "/connections", "/settings"]) {
      const response = await page.goto(path);
      expect(response?.ok()).toBe(true);
      await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/$" : path}`));
      await expect(page.locator("main")).toBeVisible();
    }
  });
});
