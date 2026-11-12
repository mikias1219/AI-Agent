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
    await page.request.post("/api/onboarding/wizard", {
      data: { name: owner.name, timezone: "UTC" },
    });
  });

  test("chat gets a reply from the fake provider", async ({ page }) => {
    await page.goto("/chat");
    await page.getByLabel("Message your agent").fill("Hello agent");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("Hello agent")).toBeVisible();
    await expect(page.getByText("Okay.").or(page.getByText(/no local model/))).toBeVisible();
  });

  test("chat turns are recorded as agent runs with a replayable event stream", async ({ page }) => {
    await page.goto("/chat");
    await page.getByLabel("Message your agent").fill("Record this run");
    await page.getByRole("button", { name: "Send" }).click();
    await expect(page.getByText("Okay.").or(page.getByText(/no local model/))).toBeVisible();

    let run: { id: string; status: string; prompt_version: string } | undefined;
    await expect
      .poll(async () => {
        const runs = await (await page.request.get("/api/runs")).json();
        run = runs.find((item: { input: string }) => item.input === "Record this run");
        return run?.status ?? null;
      })
      .toBe("completed");
    expect(run).toBeTruthy();
    expect(run!.prompt_version).toMatch(/^system_v1@\d{4}-\d{2}-\d{2}\//);

    const stream = await page.request.get(`/api/runs/${run!.id}/events`);
    const types = (await stream.text())
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line).type);
    expect(types[0]).toBe("run.started");
    expect(types.at(-1)).toBe("run.completed");
  });

  test("chat shows a collapsible step trail under the answer", async ({ page }) => {
    const events = [
      { seq: 1, type: "run.started", data: { session_id: "s-1" } },
      { seq: 2, type: "tool.started", data: { call_id: "c1", name: "task_list", arguments: {} } },
      {
        seq: 3,
        type: "tool.finished",
        data: { call_id: "c1", name: "task_list", ok: true, output: "2 tasks", duration_ms: 31 },
      },
      { seq: 4, type: "run.completed", data: { reply: "You have 2 tasks.", stop_reason: null } },
    ].map((event) => JSON.stringify({ ...event, run_id: "run-1" }));
    await page.route("**/api/runs", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 202,
            json: { id: "run-1", session_id: "s-1", status: "running" },
          })
        : route.fallback(),
    );
    await page.route("**/api/runs/run-1/events*", (route) =>
      route.fulfill({ contentType: "application/x-ndjson", body: events.join("\n") + "\n" }),
    );

    await page.goto("/chat");
    await page.getByLabel("Message your agent").fill("What is on my list?");
    await page.getByRole("button", { name: "Send" }).click();

    await expect(page.getByText("You have 2 tasks.")).toBeVisible();
    const toggle = page.getByRole("button", { name: "Used 1 tool" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.getByText("Task list")).toBeVisible();
    await expect(page.getByText("31 ms")).toBeVisible();
  });

  test("Stop cancels the run and keeps the progress summary", async ({ page }) => {
    let cancelled: () => void = () => {};
    const cancelSeen = new Promise<void>((resolve) => (cancelled = resolve));
    const line = (event: object) => JSON.stringify({ run_id: "run-2", ...event }) + "\n";
    await page.route("**/api/runs", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 202,
            json: { id: "run-2", session_id: "s-2", status: "running" },
          })
        : route.fallback(),
    );
    await page.route("**/api/runs/run-2/cancel", (route) => {
      cancelled();
      return route.fulfill({ status: 202, json: { id: "run-2", status: "running" } });
    });
    await page.route("**/api/runs/run-2/events*", async (route) => {
      await cancelSeen;
      await route.fulfill({
        contentType: "application/x-ndjson",
        body:
          line({ seq: 1, type: "run.started", data: { session_id: "s-2" } }) +
          line({
            seq: 2,
            type: "run.failed",
            data: { status: "cancelled", reply: "I stopped because you asked me to." },
          }),
      });
    });

    await page.goto("/chat");
    await page.getByLabel("Message your agent").fill("Do a long job");
    await page.getByRole("button", { name: "Send" }).click();
    await page.getByRole("button", { name: "Stop" }).click();

    await expect(page.getByText("I stopped because you asked me to.")).toBeVisible();
    await expect(page.getByText("Stopped at your request.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Send" })).toBeVisible();
  });

  test("chat pauses on an approval card, then resumes the same answer after Approve", async ({
    page,
  }) => {
    const line = (event: object) => JSON.stringify({ run_id: "run-3", ...event }) + "\n";
    const required = {
      approval_id: "ap-1",
      tool: "google_gmail_send",
      arguments: { to: "ana@example.com", subject: "Lunch", body: "Friday at noon?" },
      summary: "Send an email via Gmail",
      risk: "high",
      untrusted_content: true,
      arguments_hash: "h1",
      expires_at: new Date(Date.now() + 23 * 3600_000).toISOString(),
      durable: true,
    };
    let decisions = 0;
    await page.route("**/api/runs", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 202,
            json: { id: "run-3", session_id: "s-3", status: "running" },
          })
        : route.fallback(),
    );
    await page.route("**/api/runs/run-3/events*", (route) => {
      const after = Number(new URL(route.request().url()).searchParams.get("after") ?? "0");
      const body =
        after === 0
          ? line({ seq: 1, type: "run.started", data: { session_id: "s-3" } }) +
            line({
              seq: 2,
              type: "tool.started",
              data: { call_id: "c1", name: "google_gmail_send" },
            }) +
            line({ seq: 3, type: "approval.required", data: required })
          : line({
              seq: 4,
              type: "approval.resolved",
              data: { approval_id: "ap-1", decision: "approved" },
            }) +
            line({
              seq: 5,
              type: "tool.finished",
              data: { call_id: "c1", name: "google_gmail_send", ok: true, output: "sent" },
            }) +
            line({ seq: 6, type: "run.completed", data: { reply: "I sent the email to Ana." } });
      return route.fulfill({ contentType: "application/x-ndjson", body });
    });
    await page.route("**/api/approvals/ap-1/decision", (route) => {
      decisions += 1;
      return route.fulfill({
        json: {
          id: "ap-1",
          decision: "approved",
          status: "executed",
          executed: true,
          ok: true,
          result: "sent",
          run_id: "run-3",
        },
      });
    });

    await page.goto("/chat");
    await page.getByLabel("Message your agent").fill("Email Ana about lunch");
    await page.getByRole("button", { name: "Send" }).click();

    const card = page.getByRole("region", { name: "Approval: Send email" });
    await expect(card).toBeVisible();
    await expect(card.getByText("Send an email via Gmail")).toBeVisible();
    await expect(card.getByText("High risk")).toBeVisible();
    await expect(card.getByText("ana@example.com")).toBeVisible();
    await expect(card.getByText("Friday at noon?")).toBeVisible();
    await expect(card.getByText(/came after reading an email/)).toBeVisible();
    await expect(card.getByText(/Expires in 2\d h/)).toBeVisible();
    await expect(card.getByRole("button", { name: "Edit then approve" })).toBeVisible();
    await expect(card.getByRole("button", { name: "Deny" })).toBeVisible();

    await card.getByRole("button", { name: "Approve", exact: true }).click();
    await expect(page.getByText("I sent the email to Ana.")).toBeVisible();
    await expect(card).toBeHidden();
    expect(decisions).toBe(1);
  });

  test("Edit then approve creates a new approval and approves that one", async ({ page }) => {
    const base = {
      run_id: "run-4",
      tool_name: "google_gmail_send",
      summary: "Send an email via Gmail",
      arguments_hash: "h1",
      risk: "high",
      untrusted_content: false,
      status: "pending",
      user_id: "dashboard",
      session_id: "s-4",
      origin: "dashboard",
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + 3600_000).toISOString(),
      decided_at: null,
      edited_from: null,
      result: "",
      actionable: true,
    };
    const original = {
      ...base,
      id: "ap-old",
      arguments: { to: "ana@example.com", subject: "Lunch", body: "Friday?" },
    };
    const calls: string[] = [];
    let edited: unknown = null;
    await page.route("**/api/approvals", (route) =>
      route.request().method() === "GET" ? route.fulfill({ json: [original] }) : route.fallback(),
    );
    await page.route("**/api/approvals/ap-old/edit", async (route) => {
      calls.push("edit");
      edited = route.request().postDataJSON();
      return route.fulfill({
        status: 201,
        json: {
          ...base,
          id: "ap-new",
          edited_from: "ap-old",
          arguments_hash: "h2",
          arguments: (edited as { arguments: object }).arguments,
        },
      });
    });
    await page.route("**/api/approvals/ap-new/decision", (route) => {
      calls.push("decide-new");
      return route.fulfill({
        json: {
          id: "ap-new",
          decision: "approved",
          status: "executed",
          executed: true,
          ok: true,
          result: "sent",
          run_id: "run-4",
        },
      });
    });

    await page.goto("/tasks");
    await page.getByRole("tab", { name: /Approvals/ }).click();
    const card = page.getByRole("region", { name: "Approval: Send email" });
    await expect(card.getByText("Friday?")).toBeVisible();
    await card.getByRole("button", { name: "Edit then approve" }).click();
    await card.getByLabel("Body").fill("Friday at 1pm?");
    await card.getByRole("button", { name: "Approve edited" }).click();

    await expect.poll(() => calls).toEqual(["edit", "decide-new"]);
    expect(edited).toMatchObject({ arguments: { body: "Friday at 1pm?", to: "ana@example.com" } });
  });

  test("create a task and see the empty approvals queue", async ({ page }) => {
    await page.goto("/tasks");
    await page.getByLabel("New task").fill("Ship Phase 0");
    await page.getByRole("button", { name: "Add task" }).click();
    await expect(page.getByText("Ship Phase 0")).toBeVisible();

    await page.getByRole("tab", { name: "Overdue" }).click();
    await expect(page.getByText("Nothing overdue")).toBeVisible();
    await page.getByRole("tab", { name: "All" }).click();
    await page.getByRole("button", { name: "Open Ship Phase 0" }).click();
    await expect(page.getByRole("dialog", { name: "Task details" })).toBeVisible();
    await page.keyboard.press("Escape");

    await page.getByRole("tab", { name: /Approvals/ }).click();
    await expect(page.getByText("Nothing waiting")).toBeVisible();
  });

  test("key routes render", async ({ page }) => {
    for (const path of [
      "/",
      "/inbox",
      "/goals",
      "/calendar",
      "/mail",
      "/memory",
      "/routines",
      "/activity",
      "/connections",
      "/settings",
      "/help",
    ]) {
      const response = await page.goto(path);
      expect(response?.ok()).toBe(true);
      await expect(page).toHaveURL(new RegExp(`${path === "/" ? "/$" : path}`));
      await expect(page.locator("main")).toBeVisible();
    }
  });

  test("sidebar shows grouped nav labels and header chrome (desktop)", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    const nav = page.getByRole("navigation", { name: "Primary" });
    for (const label of [
      "Today",
      "Chat",
      "Inbox",
      "Tasks",
      "Goals",
      "Calendar",
      "Mail",
      "Memory",
      "Routines",
      "Activity",
      "Connections",
      "Settings",
      "Help",
    ]) {
      await expect(nav.getByRole("link", { name: label })).toBeVisible();
    }
    await expect(nav.getByText("My work", { exact: true })).toBeVisible();
    await expect(nav.getByText("AURA", { exact: true })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Automations" })).toHaveCount(0);

    await expect(page.getByRole("button", { name: /Notifications/ })).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Autonomy preset: Balanced" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Pause agent/ })).toBeDisabled();

    const drawer = page.getByRole("dialog", { name: "Quick ask" });
    // Retry the shortcut: the first press can land before the page hydrates.
    await expect(async () => {
      await page.keyboard.press("Control+k");
      await expect(drawer).toBeVisible({ timeout: 1000 });
    }).toPass();
    await page.keyboard.press("Escape");
    await expect(drawer).toBeHidden();
  });

  test("quick ask drawer starts a run and shows the reply", async ({ page }) => {
    await page.route("**/api/runs", (route) =>
      route.request().method() === "POST"
        ? route.fulfill({
            status: 202,
            json: { id: "run-qa", session_id: "s-qa", status: "running" },
          })
        : route.fallback(),
    );
    await page.route("**/api/runs/run-qa/events*", (route) =>
      route.fulfill({
        contentType: "application/x-ndjson",
        body:
          [
            { seq: 1, type: "run.started", data: { session_id: "s-qa" } },
            { seq: 2, type: "run.completed", data: { reply: "Quick answer." } },
          ]
            .map((event) => JSON.stringify({ run_id: "run-qa", ...event }))
            .join("\n") + "\n",
      }),
    );
    await page.setViewportSize({ width: 1280, height: 800 });
    await page.goto("/");
    await page.getByRole("button", { name: "Quick ask" }).first().click();
    await page.getByLabel("Ask AURA", { exact: true }).fill("What now?");
    await page.getByRole("button", { name: "Ask", exact: true }).click();
    await expect(page.getByText("Quick answer.")).toBeVisible();
  });

  test("mobile 360 opens the grouped menu", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 740 });
    await page.goto("/");
    await page.getByRole("button", { name: "Open menu" }).click();
    const nav = page.getByRole("navigation", { name: "Primary" });
    await expect(nav.getByRole("link", { name: "Goals" })).toBeVisible();
    await expect(nav.getByRole("link", { name: "Routines" })).toBeVisible();
  });

  test("legacy /automations redirects to /routines", async ({ page }) => {
    await page.goto("/automations");
    await expect(page).toHaveURL(/\/routines$/);
  });

  test("Today v2 renders the /api/today aggregate and Stop cancels the active run", async ({
    page,
  }) => {
    let cancelled = false;
    const payload = (activeRun: object | null) => ({
      greeting: { name: "Smoke Owner", summary: "One approval needs you." },
      needs_you: [
        {
          kind: "approval",
          id: "ap-9",
          run_id: "r1",
          tool_name: "email_send",
          summary: "Send a reply",
          risk: "high",
        },
      ],
      now_next: { events: [], calendar_connected: false, active_run: activeRun },
      plan: { tasks: [], plan_id: null },
      goals: [],
      since_last_looked: [],
      onboarding: {
        wizard_completed: true,
        checklist_complete: true,
        show_checklist: false,
        items: [],
      },
      connections: {
        warnings: [
          {
            id: "google",
            severity: "info",
            message: "Calendar is not connected.",
            action: { label: "Connect", href: "/connections" },
          },
        ],
      },
      briefing: { text: null, summary: null, sections: [], run_id: null },
    });
    await page.route("**/api/today", (route) =>
      route.fulfill({
        json: payload(
          cancelled
            ? null
            : {
                id: "run-t",
                status: "running",
                origin: "chat",
                input: "Plan my week",
                created_at: null,
              },
        ),
      }),
    );
    await page.route("**/api/runs/run-t/cancel", (route) => {
      cancelled = true;
      return route.fulfill({ status: 202, json: { id: "run-t", status: "cancelled" } });
    });
    await page.goto("/");
    await expect(page.getByTestId("today-summary")).toHaveText("One approval needs you.");
    await expect(page.getByRole("heading", { name: "Needs you" })).toBeVisible();
    await expect(page.getByText("Calendar is not connected.").first()).toBeVisible();
    await expect(page.getByText("No upcoming events")).toHaveCount(0);
    await page.getByRole("button", { name: "Stop" }).click();
    await expect(page.getByTestId("today-active-run")).toHaveCount(0);
  });

  test("first-run wizard then Today checklist", async ({ page }) => {
    await page.request.post("/api/onboarding/wizard", {
      data: { name: "Smoke Owner", timezone: "UTC" },
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Good (morning|afternoon|evening)/ }),
    ).toBeVisible();
    const checklist = page.getByRole("heading", { name: "Getting started" });
    if (await checklist.isVisible().catch(() => false)) {
      await expect(page.getByText("Ask AURA something")).toBeVisible();
      await page.getByRole("button", { name: "Skip briefing for now" }).click();
      await expect(page.getByText("Set up daily briefing")).toBeVisible();
    }
  });
});
