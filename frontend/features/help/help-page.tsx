"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { PageFrame } from "@/components/ui/page-frame";
import { getGoogleStatus } from "@/lib/api/google";

type PromptGroup = { id: string; title: string; prompts: string[] };

const ALWAYS: PromptGroup[] = [
  {
    id: "tasks",
    title: "Tasks and reminders",
    prompts: [
      "Add a task to renew my passport by Friday",
      "What is on my plate today?",
      "Remind me to call the dentist tomorrow at 9",
      "Mark the passport task as done",
      "Plan my week around my open tasks",
    ],
  },
  {
    id: "memory",
    title: "Memory",
    prompts: [
      "Remember that I prefer morning meetings",
      "What do you remember about my travel preferences?",
      "Remember that my manager is on leave in August",
      "Forget what you saved about my commute",
      "Which memories did you use for your last answer?",
    ],
  },
];

const GOOGLE: Record<"gmail" | "calendar" | "drive", PromptGroup> = {
  gmail: {
    id: "gmail",
    title: "Gmail",
    prompts: [
      "Summarise my unread email from today",
      "Draft a reply to the latest message from my manager",
      "Find the email about the hotel booking",
      "Which emails need a reply from me?",
      "Archive the newsletters from this week",
    ],
  },
  calendar: {
    id: "calendar",
    title: "Calendar",
    prompts: [
      "What is on my calendar tomorrow?",
      "Find two hours of focus time this week",
      "Move my 3pm meeting to Thursday",
      "Create a lunch event with Ana on Friday at noon",
      "Do I have any conflicts next week?",
    ],
  },
  drive: {
    id: "drive",
    title: "Drive",
    prompts: [
      "Find the Q3 planning document",
      "Summarise the latest file in my Drive",
      "Search Drive for the lease agreement",
      "Create a doc called Meeting notes",
      "Read the file called Budget 2026",
    ],
  },
};

const SHORTCUTS = [
  { keys: "Ctrl + K  or  Cmd + K", does: "Open the command palette" },
  { keys: "Arrow keys, Enter", does: "Choose a result in the palette" },
  { keys: "Esc", does: "Close a palette, menu or drawer" },
  { keys: "Arrow keys", does: "Move between tabs" },
];

export function HelpPage() {
  const [groups, setGroups] = useState<PromptGroup[]>(ALWAYS);

  useEffect(() => {
    let cancelled = false;
    getGoogleStatus()
      .then((status) => {
        if (cancelled || !status.connected) return;
        const connected = (["gmail", "calendar", "drive"] as const)
          .filter((key) => status.services?.[key])
          .map((key) => GOOGLE[key]);
        setGroups([...connected, ...ALWAYS]);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <PageFrame width="chat">
      <Card
        id="help-prompts-heading"
        title="Try asking"
        description="Copy a line into Chat. Anything that sends or changes data waits for your approval."
      >
        <div className="flex flex-col gap-5">
          {groups.map((group) => (
            <section key={group.id} aria-label={group.title}>
              <h3 className="text-sm font-semibold text-[var(--ink)]">{group.title}</h3>
              <ul className="mt-2 flex flex-col gap-1 text-sm text-[var(--muted)]">
                {group.prompts.map((prompt) => (
                  <li key={prompt}>“{prompt}”</li>
                ))}
              </ul>
            </section>
          ))}
          <p className="text-xs text-[var(--muted)]">
            Gmail, Calendar and Drive prompts appear when Google is connected under Connections.
          </p>
        </div>
      </Card>

      <Card id="help-shortcuts-heading" title="Keyboard shortcuts">
        <dl className="flex flex-col gap-2 text-sm">
          {SHORTCUTS.map((row) => (
            <div key={row.keys} className="flex flex-wrap items-baseline justify-between gap-2">
              <dt className="text-[var(--ink)]">{row.does}</dt>
              <dd>
                <kbd className="rounded border border-[var(--border)] bg-[var(--canvas)] px-1.5 py-0.5 text-xs text-[var(--ink)]">
                  {row.keys}
                </kbd>
              </dd>
            </div>
          ))}
        </dl>
      </Card>
    </PageFrame>
  );
}
