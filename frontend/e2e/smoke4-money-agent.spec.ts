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

  test("typing in a side panel keeps focus in the field", async ({ page }) => {
    await page.goto("/library?tab=notes");
    await page.getByRole("button", { name: "New note" }).click();
    const title = page.locator("#entry-title");
    await expect(title).toBeFocused();
    await title.pressSequentially("Mid-week");
    await expect(title).toBeFocused();
    await expect(title).toHaveValue("Mid-week");
    await page.keyboard.press("Escape");
  });

  test("mail opens in a side panel from any page", async ({ page }) => {
    await page.route("**/api/google/status", (route) =>
      route.fulfill({
        json: {
          oauth_configured: true,
          connected: true,
          email: "me@example.com",
          services: { gmail: true, calendar: false, drive: false },
        },
      }),
    );
    await page.route("**/api/google/gmail*", (route) =>
      route.fulfill({
        json: {
          items: [
            {
              id: "m1",
              from: "Abel <abel@example.com>",
              subject: "Can you review the budget?",
              snippet: "Please reply by Friday",
              receivedAt: "2026-11-27T08:00:00Z",
            },
          ],
          page: 1,
          page_size: 20,
          total: 1,
        },
      }),
    );
    await page.goto("/money");
    await page.getByRole("button", { name: /^Mail/ }).click();
    const panel = page.getByRole("dialog", { name: "Mail" });
    await expect(panel.getByText("Can you review the budget?")).toBeVisible();
    await panel.getByText("Can you review the budget?").click();
    await expect(panel.getByRole("button", { name: "Draft a reply" })).toBeVisible();
    await expect(panel.getByRole("link", { name: /Open in Gmail/ })).toBeVisible();
    await expect(page).toHaveURL(/\/money/);
  });

  test("Get new words runs in the Learn agent and sends saved words as hidden context", async ({
    page,
  }) => {
    let sent: { text?: string; context?: string } = {};
    await page.route("**/api/runs", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      sent = route.request().postDataJSON();
      await route.fulfill({
        status: 202,
        json: { id: "run-w", session_id: "s-w", status: "running" },
      });
    });
    await page.route("**/api/runs/run-w/events*", (route) =>
      route.fulfill({
        contentType: "application/x-ndjson",
        body:
          JSON.stringify({
            run_id: "run-w",
            seq: 1,
            type: "run.completed",
            data: { reply: "Saved 3 new words." },
          }) + "\n",
      }),
    );
    await page.goto("/learn");
    await page.getByRole("button", { name: "3", exact: true }).click();
    await page.getByRole("button", { name: "Get 3 new words" }).click();
    const panel = page.getByRole("dialog", { name: "Learn agent" });
    await expect(panel.getByText("Saved 3 new words.")).toBeVisible();
    await expect(page).toHaveURL(/\/learn/);
    expect(sent.text).toContain("Teach me 3 new English words");
    expect(sent.text).not.toContain("Learn agent");
    expect(sent.context).toContain("exactly 3 words");
  });
});
