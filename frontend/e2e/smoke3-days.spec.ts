import { expect, test, type Page } from "@playwright/test";

// Days, achievements and sync against the real API (fake model provider, temp SQLite).
// Runs after smoke.spec.ts and smoke2-life.spec.ts, so the owner account already exists.
// Google is not configured in this environment, so sync must fail honestly, never pretend.
test.describe.configure({ mode: "serial" });

const owner = { email: "owner@example.com", password: "smoke-pass-12345" };

function isoDay(offsetDays = 0): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offsetDays);
  return d.toISOString().slice(0, 10);
}

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

async function createTask(page: Page, data: Record<string, unknown>) {
  const res = await page.request.post("/api/tasks", { data });
  expect(res.status(), await res.text()).toBe(201);
  return (await res.json()) as { id: string; [k: string]: unknown };
}

test.describe("days and achievements", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
  });

  test("a task with a target is judged by what was really done", async ({ page }) => {
    const today = isoDay();
    const partial = await createTask(page, {
      title: "30 push-ups",
      target_value: 30,
      target_unit: "push-ups",
      plan_date: today,
    });
    expect(partial.plan_date).toBe(today);
    expect(partial.target_value).toBe(30);

    // 18 of 30 is partly done: the task closes as done, with the outcome kept.
    const done = await page.request.post(`/api/tasks/${partial.id}/complete`, {
      data: { actual_value: 18 },
    });
    expect(done.ok()).toBeTruthy();
    const closed = await done.json();
    expect(closed.outcome).toBe("partial");
    expect(closed.status).toBe("done");
    expect(closed.actual_value).toBe(18);

    // The full target is achieved; zero is missed and does not count as done.
    const full = await createTask(page, {
      title: "Read 20 pages",
      target_value: 20,
      target_unit: "pages",
      plan_date: today,
    });
    const achieved = await (
      await page.request.post(`/api/tasks/${full.id}/complete`, { data: { actual_value: 20 } })
    ).json();
    expect(achieved.outcome).toBe("achieved");

    const none = await createTask(page, { title: "Cold shower", plan_date: today });
    const missed = await (
      await page.request.post(`/api/tasks/${none.id}/complete`, { data: { outcome: "missed" } })
    ).json();
    expect(missed.outcome).toBe("missed");
    expect(missed.status).toBe("cancelled");

    const bad = await page.request.post(`/api/tasks/${none.id}/complete`, {
      data: { actual_value: -5 },
    });
    // Rejected either way; task routes validate with the framework, so this is a 422.
    expect([400, 422]).toContain(bad.status());
  });

  test("the day view lists the tasks with outcomes and a score", async ({ page }) => {
    const today = isoDay();
    const day = await (await page.request.get(`/api/days/${today}`)).json();
    const byTitle = Object.fromEntries(
      (day.tasks as { title: string; outcome: string | null }[]).map((t) => [t.title, t.outcome]),
    );
    expect(byTitle["30 push-ups"]).toBe("partial");
    expect(byTitle["Read 20 pages"]).toBe("achieved");
    expect(byTitle["Cold shower"]).toBe("missed");
    expect(day.summary.partial).toBeGreaterThanOrEqual(1);
    expect(day.summary.achieved).toBeGreaterThanOrEqual(1);
    expect(day.summary.score).not.toBeNull();
    expect(day.calendar_connected).toBe(false);
    expect(day.events).toEqual([]);

    await page.goto("/tasks");
    await expect(page.getByText("30 push-ups").first()).toBeVisible();
    await expect(page.getByText(/Partly 18\/30/).first()).toBeVisible();
    await expect(page.getByText(/Achieved 20\/20/).first()).toBeVisible();
  });

  test("reopening a task clears its outcome", async ({ page }) => {
    const today = isoDay();
    const day = await (await page.request.get(`/api/days/${today}`)).json();
    const task = day.tasks.find((t: { title: string }) => t.title === "30 push-ups");
    const reopened = await page.request.patch(`/api/tasks/${task.id}`, {
      data: { status: "planned" },
    });
    expect(reopened.ok(), await reopened.text()).toBeTruthy();
    const body = await reopened.json();
    expect(body.status).toBe("planned");
    expect(body.outcome).toBeNull();
    expect(body.actual_value).toBeNull();
  });

  test("unfinished tasks carry over to tomorrow and finished ones stay", async ({ page }) => {
    const today = isoDay();
    const tomorrow = isoDay(1);
    const open = await createTask(page, { title: "Call the dentist", plan_date: today });
    const result = await (
      await page.request.post(`/api/days/${today}/carry-over`, { data: {} })
    ).json();
    expect(result.to).toBe(tomorrow);
    expect(result.task_ids).toContain(open.id);
    expect(result.moved).toBeGreaterThanOrEqual(1);

    const tomorrowDay = await (await page.request.get(`/api/days/${tomorrow}`)).json();
    expect(tomorrowDay.tasks.map((t: { id: string }) => t.id)).toContain(open.id);

    // Finished tasks were not moved.
    const todayDay = await (await page.request.get(`/api/days/${today}`)).json();
    const titles = todayDay.tasks.map((t: { title: string }) => t.title);
    expect(titles).toContain("Read 20 pages");
    expect(titles).not.toContain("Call the dentist");
  });

  test("range and stats answer for the owner's days", async ({ page }) => {
    const range = await page.request.get(`/api/days/range?from=${isoDay(-3)}&to=${isoDay(1)}`);
    expect(range.ok()).toBeTruthy();
    const rows = await range.json();
    expect(rows.some((r: { date: string }) => r.date === isoDay())).toBe(true);

    const tooLong = await page.request.get(`/api/days/range?from=${isoDay(-90)}&to=${isoDay()}`);
    expect(tooLong.status()).toBe(400);

    const stats = await (await page.request.get("/api/days/stats")).json();
    expect(typeof stats.streak_days).toBe("number");
    expect(stats.week.planned).toBeGreaterThanOrEqual(1);
  });

  test("Today carries the day summary", async ({ page }) => {
    const today = await (await page.request.get("/api/today")).json();
    expect(today.day.summary.planned).toBeGreaterThanOrEqual(1);
    expect(typeof today.day.date).toBe("string");
  });
});

test.describe("Drive and Calendar sync", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
  });

  test("Drive backup is off and asks first when Google is not connected", async ({ page }) => {
    const status = await (await page.request.get("/api/drive-sync/status")).json();
    expect(status.connected).toBe(false);
    expect(status.mode).toBe("ask");
    expect(status.pending.notes).toBeGreaterThanOrEqual(1);

    // Running without Google must fail clearly and write nothing.
    const run = await page.request.post("/api/drive-sync/run", { data: {} });
    expect(run.status()).toBe(409);
    expect((await run.json()).detail).toBe("Google Drive is not connected.");

    const items = await (await page.request.get("/api/drive-sync/items")).json();
    expect(items).toEqual([]);
  });

  test("Calendar sync also refuses honestly without Google", async ({ page }) => {
    const status = await (await page.request.get("/api/calendar-sync/status")).json();
    expect(status.connected).toBe(false);
    expect(status.mode).toBe("ask");
    const run = await page.request.post("/api/calendar-sync/run", { data: {} });
    expect(run.status()).toBe(409);
  });

  test("the sync settings can be switched and persist", async ({ page }) => {
    const on = await page.request.patch("/api/drive-sync/settings", {
      data: { enabled: true, include: { notes: true, diary: true, daily: true } },
    });
    expect(on.ok(), await on.text()).toBeTruthy();
    expect((await on.json()).enabled).toBe(true);
    const again = await (await page.request.get("/api/drive-sync/status")).json();
    expect(again.enabled).toBe(true);
    await page.request.patch("/api/drive-sync/settings", { data: { enabled: false } });
  });

  test("Connections shows Backup and sync without claiming anything synced", async ({ page }) => {
    await page.goto("/connections");
    await expect(page.getByText("Backup and sync").first()).toBeVisible();
    await expect(page.getByText(/Google Drive backup/i).first()).toBeVisible();
    await expect(page.getByText(/Last (sync|backup)/i)).toHaveCount(0);
  });

  test("the evening wrap-up is a real, enforced notification option", async ({ page }) => {
    const prefs = await (await page.request.get("/api/profile/notifications")).json();
    expect(prefs.enforced).toContain("daily_wrapup");
    expect(prefs.enforced).toContain("wrapup_time");
  });

  test("achievements are part of the owner's export", async ({ page }) => {
    const text = await (await page.request.get("/api/export")).text();
    expect(text).toContain("push-ups");
    expect(text).toContain("Read 20 pages");
  });
});
