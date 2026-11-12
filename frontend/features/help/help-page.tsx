"use client";

const LOOP = [
  { title: "Sense", body: "Read calendar, mail, tasks, and memory you approved." },
  { title: "Plan", body: "Propose steps and drafts. Nothing leaves without a clear next action." },
  { title: "Ask", body: "Hard ceilings and prepare/execute commits land in Inbox for one-tap OK." },
  { title: "Act", body: "Approved tools run through the registry. Pause stops non-read work." },
  { title: "Learn", body: "Save memories only when you ask or confirm. Activity keeps a trail." },
];

const WORKFLOWS = [
  {
    title: "Daily briefing",
    body: "When the scheduler is on, AURA builds today’s calendar, due tasks and pending approvals for Today and optional Telegram — respecting quiet hours and the daily cap.",
  },
  {
    title: "Inbox to action",
    body: "Ask AURA to reply to an email. It drafts, shows an approval card, and sends only after you approve.",
  },
  {
    title: "Plan my week",
    body: "Ask for a plan. AURA proposes tasks and calendar changes; commits wait for approval.",
  },
  {
    title: "Never forget",
    body: "Say “remind me…” or create a task. Delivery uses Telegram and Inbox; late deliveries are labeled.",
  },
  {
    title: "Remember me",
    body: "Ask AURA to remember a preference. Confirm the Save chip. Later answers show Used memory chips.",
  },
];

export function HelpPage() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Help</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          How AURA works
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Sense → Plan → Ask → Act → Learn. AURA reads and drafts on its own; anything that leaves
          your hands waits for approval.
        </p>
      </header>

      <ol className="grid gap-3 sm:grid-cols-5">
        {LOOP.map((item, index) => (
          <li
            key={item.title}
            className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-3"
          >
            <p className="text-xs font-medium text-[var(--accent)]">
              {index + 1}. {item.title}
            </p>
            <p className="mt-2 text-xs text-[var(--muted)]">{item.body}</p>
          </li>
        ))}
      </ol>

      <section className="flex flex-col gap-4">
        <h2 className="text-sm font-semibold text-[var(--ink)]">Five workflows</h2>
        <ol className="flex flex-col gap-4">
          {WORKFLOWS.map((item, index) => (
            <li
              key={item.title}
              className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4"
            >
              <p className="text-xs font-medium text-[var(--muted)]">W{index + 1}</p>
              <h3 className="mt-1 text-sm font-semibold text-[var(--ink)]">{item.title}</h3>
              <p className="mt-2 text-sm text-[var(--muted)]">{item.body}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
