import { expect, test, type Page } from "@playwright/test";

// Redesign: an agent in every module, add buttons on desktop, and the payslip calculator.
// Runs after smoke.spec.ts, which creates the single owner account.
test.describe.configure({ mode: "serial" });

const owner = { email: "owner@example.com", password: "smoke-pass-12345" };

async function signIn(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(owner.email);
  await page.getByLabel("Password", { exact: true }).fill(owner.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
  await page.request.post("/api/onboarding/wizard", {
    data: { name: "Smoke Owner", timezone: "UTC" },
  });
}

test.describe("money redesign", () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 860 });
    await signIn(page);
  });

  test("every module shows its agent bar and the panel opens with prompts", async ({ page }) => {
    for (const [path, name] of [
      ["/", "Day agent"],
      ["/tasks", "Plan agent"],
      ["/money", "Money agent"],
      ["/learn", "Learn agent"],
      ["/library", "Notes agent"],
    ] as const) {
      await page.goto(path);
      await expect(page.getByRole("region", { name })).toBeVisible();
    }
    await page.goto("/money");
    await page
      .getByRole("region", { name: "Money agent" })
      .getByRole("button", { name: /Ask/ })
      .click();
    const panel = page.getByRole("dialog", { name: "Money agent" });
    await expect(panel).toBeVisible();
    await expect(panel.getByRole("button", { name: "How much is left this month?" })).toBeVisible();
  });

  test("Money has Add expense and Add income on desktop", async ({ page }) => {
    await page.goto("/money?tab=activity");
    await expect(page.getByRole("tab", { name: "Activity", selected: true })).toBeVisible();
    await page.getByRole("button", { name: "Add income" }).first().click();
    const sheet = page.getByRole("dialog", { name: "Add" });
    await expect(sheet).toBeVisible();
    await expect(sheet.getByRole("button", { name: "Income" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test("a 35,000 basic salary previews tax 10,200, pension 2,450 and net 22,350", async ({
    page,
  }) => {
    await page.goto("/money?tab=income");
    await page.getByLabel("Basic salary").fill("35000");
    const pay = page.getByRole("region", { name: "Add a payslip" });
    await expect(pay.getByText("Net pay")).toBeVisible();
    await expect(pay).toContainText("10,200");
    await expect(pay).toContainText("2,450");
    await expect(pay).toContainText("22,350");
    await expect(pay).toContainText("35% − 2,050");
  });
});
