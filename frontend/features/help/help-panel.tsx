"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const BY_PATH: Record<string, { title: string; body: string; prompts: string[] }> = {
  "/": {
    title: "Today",
    body: "Your home screen: ask AURA, approve waiting actions, see due work, and finish getting started.",
    prompts: ["What should I focus on today?", "Create a task for Friday"],
  },
  "/chat": {
    title: "Chat",
    body: "Talk with your agent. Step trails show tools. Approvals and Save chips appear under answers.",
    prompts: ["Remember that I prefer morning meetings", "List my open tasks"],
  },
  "/inbox": {
    title: "Inbox",
    body: "Decide on pending approvals. Reminders list deliveries (late labeled if over five minutes).",
    prompts: [],
  },
  "/routines": {
    title: "Routines",
    body: "Daily briefing schedule, enable/disable, and Run now. Same approval gates as chat.",
    prompts: [],
  },
  "/tasks": {
    title: "Tasks",
    body: "Your commitments. Views cover today, upcoming and overdue. Approvals live on a tab too.",
    prompts: ["Create a task to pay rent on Friday"],
  },
  "/goals": {
    title: "Goals",
    body: "Longer outcomes AURA will plan and track with you. Nothing is shown until you add one.",
    prompts: [],
  },
  "/calendar": {
    title: "Calendar",
    body: "Your schedule from a connected calendar. Empty until Google is connected.",
    prompts: [],
  },
  "/mail": {
    title: "Mail",
    body: "Mail AURA has read or drafted. Empty until Google is connected.",
    prompts: [],
  },
  "/memory": {
    title: "Memory",
    body: "What AURA knows about you. Only saved when you ask or confirm a Save chip.",
    prompts: ["Remember my timezone is Africa/Addis_Ababa"],
  },
  "/connections": {
    title: "Connections",
    body: "Telegram and Google wiring. Start Telegram so AURA can listen and deliver.",
    prompts: [],
  },
  "/activity": {
    title: "Activity",
    body: "Audit log of what happened. Use it to verify sends and approvals.",
    prompts: [],
  },
  "/settings": {
    title: "Settings",
    body: "Account, appearance, runtime, permissions, and Data → Forget everything.",
    prompts: [],
  },
  "/help": {
    title: "Help",
    body: "The five workflows AURA is built around.",
    prompts: [],
  },
};

export function HelpPanel() {
  const pathname = usePathname();
  const key = Object.keys(BY_PATH).find((path) =>
    path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`),
  );
  const copy = BY_PATH[key ?? "/"] ?? BY_PATH["/"];

  return (
    <aside
      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 text-sm"
      aria-label="Help for this screen"
    >
      <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Help</p>
      <h2 className="mt-1 font-semibold text-[var(--ink)]">{copy.title}</h2>
      <p className="mt-2 text-[var(--muted)]">{copy.body}</p>
      {copy.prompts.length > 0 ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-[var(--ink)]">
          {copy.prompts.map((prompt) => (
            <li key={prompt}>{prompt}</li>
          ))}
        </ul>
      ) : null}
      <Link
        href="/help"
        className="mt-3 inline-block text-[var(--accent)] underline-offset-2 hover:underline"
      >
        How to use AURA
      </Link>
    </aside>
  );
}
