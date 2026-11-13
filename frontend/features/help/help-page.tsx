"use client";

const LOOP = [
  {
    title: "Trigger",
    body: "You ask, a routine runs, an event happens, or you capture something.",
  },
  { title: "Understand", body: "Reads memory, calendar, tasks and the goal it belongs to." },
  { title: "Plan", body: "For bigger requests, shows the steps first on a plan card." },
  { title: "Act", body: "Reads and drafts freely; sends and changes wait for your OK." },
  { title: "Learn", body: "Saves memories only after you confirm. Activity keeps a trail." },
];

const WORKFLOWS = [
  {
    title: "Daily briefing",
    body: "Every morning AURA tells you what your day looks like and what needs you — after quiet hours and the daily cap.",
  },
  {
    title: "Inbox to action",
    body: "Ask AURA to reply. It drafts, shows an approval card, and sends only after you approve.",
  },
  {
    title: "Plan my time",
    body: "Ask for focus time. AURA proposes slots from your calendar; booking waits for approval.",
  },
  {
    title: "Remind and follow up",
    body: "Say “remind me…”. Delivery uses Telegram and Inbox; late deliveries are labeled.",
  },
  {
    title: "Remember me",
    body: "Ask AURA to remember a preference. Confirm the Save chip. Later answers show Used memory.",
  },
  {
    title: "Reach a goal",
    body: "Describe a goal. AURA proposes success criteria and a plan; approve before it acts.",
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
          One loop for everything. You always see what it read, what it plans, and what needs you.
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
        <h2 className="text-sm font-semibold text-[var(--ink)]">Six workflows</h2>
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
