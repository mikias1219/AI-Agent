const HUMAN_EVENTS: Record<string, string> = {
  "agent.control_changed": "Autonomy or pause changed",
  "automation.briefing": "Daily briefing ran",
  "automation.proactive_blocked": "Briefing notify blocked (quiet hours or cap)",
  "reminder.delivered": "Reminder delivered",
  "reminder.cancelled": "Reminder cancelled",
  "reminder.proactive_blocked": "Reminder notify blocked",
  "tool.paused_blocked": "Tool blocked while paused",
  "approval.decided": "Approval decided",
  "run.completed": "Agent run finished",
  "run.failed": "Agent run failed",
  "run.cancelled": "Agent run cancelled",
};

export function formatActivityEvent(event: string): string {
  if (HUMAN_EVENTS[event]) return HUMAN_EVENTS[event];
  const cleaned = event.replaceAll("_", " ").replaceAll(".", " · ");
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function formatActivityWhen(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}
