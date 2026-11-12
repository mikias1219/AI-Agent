"use client";

const WORKFLOWS = [
  {
    title: "Daily briefing",
    body: "When the scheduler is on, AURA sends today’s calendar, due tasks and pending approvals to Telegram and Today.",
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
    body: "Say “remind me…” or create a task. Delivery uses Telegram and Inbox once reminders ship.",
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
          How to use AURA
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Five workflows. AURA reads and drafts on its own; anything that leaves your hands waits
          for one-tap approval.
        </p>
      </header>
      <ol className="flex flex-col gap-4">
        {WORKFLOWS.map((item, index) => (
          <li
            key={item.title}
            className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-4"
          >
            <p className="text-xs font-medium text-[var(--muted)]">W{index + 1}</p>
            <h2 className="mt-1 text-sm font-semibold text-[var(--ink)]">{item.title}</h2>
            <p className="mt-2 text-sm text-[var(--muted)]">{item.body}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
