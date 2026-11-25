import { expect, test, type Page } from "@playwright/test";

// Life modules against the real API (fake model provider, temp SQLite).
// Runs after smoke.spec.ts, which creates the single owner account, so it only signs in.
// Data is created through the API, then the real screens must show it. This checks the
// contract between the new backend and the new frontend.
test.describe.configure({ mode: "serial" });

const owner = { email: "owner@example.com", password: "smoke-pass-12345" };

// 1x1 transparent PNG.
const PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

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

test.describe("life modules", () => {
  test.beforeEach(async ({ page }) => {
    await signIn(page);
  });

  test("sidebar links to Library and Learn", async ({ page }) => {
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav.getByRole("link", { name: "Library" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Learn" })).toBeVisible();
    await nav.getByRole("link", { name: "Library" }).click();
    await expect(page).toHaveURL(/\/library/);
  });

  test("a note and a diary entry saved through the API show in the Library", async ({ page }) => {
    const note = await page.request.post("/api/notes", {
      data: {
        kind: "note",
        title: "Trip ideas",
        body: "Visit Lalibela in January",
        tags: ["travel"],
      },
    });
    expect(note.status()).toBe(201);
    const diary = await page.request.post("/api/notes", {
      data: { kind: "diary", body: "A quiet and productive day", mood: "good" },
    });
    expect(diary.status()).toBe(201);
    const again = await page.request.post("/api/notes", {
      data: { kind: "diary", body: "second entry the same day" },
    });
    expect(again.status()).toBe(409);

    await page.goto("/library");
    await expect(page.getByText("Trip ideas")).toBeVisible();
    await page.goto("/library?tab=diary");
    await expect(page.getByText("A quiet and productive day").first()).toBeVisible();

    const stats = await (await page.request.get("/api/notes/stats")).json();
    expect(stats.wrote_diary_today).toBe(true);
    expect(stats.diary_streak_days).toBeGreaterThanOrEqual(1);
  });

  test("an uploaded image shows in Files and is served safely", async ({ page }) => {
    const created = await page.request.post("/api/files", {
      data: { name: "pixel.png", mime: "image/png", data_base64: PNG_BASE64, tags: ["test"] },
    });
    expect(created.status()).toBe(201);
    const file = await created.json();
    expect(file.kind).toBe("image");

    const content = await page.request.get(file.url);
    expect(content.status()).toBe(200);
    expect(content.headers()["content-type"]).toContain("image/png");
    expect(content.headers()["x-content-type-options"]).toBe("nosniff");

    const svg = await page.request.post("/api/files", {
      data: { name: "x.svg", mime: "image/svg+xml", data_base64: "PHN2Zy8+" },
    });
    expect(svg.status()).toBe(415);

    await page.goto("/library?tab=files");
    await expect(page.getByText("pixel.png").first()).toBeVisible();
  });

  test("saved words appear in Learn and can be reviewed", async ({ page }) => {
    const saved = await page.request.post("/api/learn/items", {
      data: {
        items: [
          {
            term: "serendipity",
            meaning: "finding something good by chance",
            example: "Meeting her was pure serendipity.",
            topic: "feelings",
          },
        ],
      },
    });
    expect(saved.status()).toBe(201);
    const [item] = await saved.json();

    await page.goto("/learn?tab=words");
    await expect(page.getByText("serendipity").first()).toBeVisible();

    await page.goto("/learn");
    await expect(page.getByText("serendipity").first()).toBeVisible();

    const reviewed = await page.request.post(`/api/learn/items/${item.id}/review`, {
      data: { result: "know" },
    });
    expect(reviewed.ok()).toBeTruthy();
    expect((await reviewed.json()).box).toBe(1);
  });

  test("a reading plan shows the next passage and advances", async ({ page }) => {
    const created = await page.request.post("/api/reading/plans", {
      data: { name: "Gospel of John", template: "gospel-of-john-21" },
    });
    expect(created.status()).toBe(201);
    const plan = await created.json();
    expect(plan.next).toBeTruthy();

    await page.goto("/learn?tab=reading");
    await expect(page.getByText(plan.next).first()).toBeVisible();

    const advanced = await page.request.post(`/api/reading/plans/${plan.id}/advance`, {
      data: { reflection: "Beginning with the Word" },
    });
    expect(advanced.ok()).toBeTruthy();
    const body = await advanced.json();
    expect(body.plan.position).toBe(1);
    expect(body.log.reference).toBe(plan.next);

    const stats = await (await page.request.get("/api/reading/stats")).json();
    expect(stats.read_today).toBe(true);
  });

  test("profile: bio and photo save, and Settings shows them", async ({ page }) => {
    const patched = await page.request.patch("/api/profile", {
      data: { bio: "I like to learn something every day", birthday: "1990-05-17" },
    });
    expect(patched.ok()).toBeTruthy();

    const photo = await page.request.put("/api/profile/photo", {
      data: { mime: "image/png", data_base64: PNG_BASE64 },
    });
    expect(photo.ok()).toBeTruthy();
    const served = await page.request.get("/api/profile/photo");
    expect(served.status()).toBe(200);
    expect(served.headers()["content-type"]).toContain("image/png");

    const profile = await (await page.request.get("/api/profile")).json();
    expect(profile.has_photo).toBe(true);
    expect(profile.bio).toBe("I like to learn something every day");

    await page.goto("/settings");
    await expect(page.getByLabel("Bio")).toHaveValue("I like to learn something every day");
  });

  test("password change rejects a wrong current password", async ({ page }) => {
    const wrong = await page.request.post("/api/auth/password", {
      data: { current_password: "not-the-password", new_password: "another-long-password-1" },
    });
    expect(wrong.status()).toBe(401);
    const weak = await page.request.post("/api/auth/password", {
      data: { current_password: owner.password, new_password: "short" },
    });
    expect(weak.status()).toBe(400);
  });

  test("notification preferences only advertise what is enforced", async ({ page }) => {
    const res = await page.request.get("/api/profile/notifications");
    expect(res.ok()).toBeTruthy();
    const prefs = await res.json();
    expect(Array.isArray(prefs.enforced)).toBe(true);
    expect(prefs.enforced).toContain("daily_briefing");
  });

  test("Today shows the life cards once the modules are used", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/Words to review/i).first()).toBeVisible();
  });

  test("the life data is part of the owner's export", async ({ page }) => {
    const res = await page.request.get("/api/export");
    expect(res.ok()).toBeTruthy();
    const text = await res.text();
    expect(text).toContain("Trip ideas");
    expect(text).toContain("serendipity");
  });
});
