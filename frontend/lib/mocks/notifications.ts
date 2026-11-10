export type NotificationKind = "approval" | "activity" | "connection";

export type ShellNotification = {
  id: string;
  title: string;
  body: string;
  href: string;
  createdAt: string;
  kind: NotificationKind;
  preview: boolean;
};

export const NOTIFICATION_PAGE_SIZE = 10;

export const mockNotifications: ShellNotification[] = [
  {
    id: "preview-approval",
    title: "Approval waiting",
    body: "A tool call is waiting for your decision.",
    href: "/tasks",
    createdAt: "2026-11-10T09:40:00.000Z",
    kind: "approval",
    preview: true,
  },
  {
    id: "preview-tasks",
    title: "Open tasks",
    body: "Review work that still needs a decision.",
    href: "/tasks",
    createdAt: "2026-11-10T08:15:00.000Z",
    kind: "approval",
    preview: true,
  },
  {
    id: "preview-activity",
    title: "Recent activity",
    body: "An audit entry is ready to review.",
    href: "/activity",
    createdAt: "2026-11-10T07:05:00.000Z",
    kind: "activity",
    preview: true,
  },
  {
    id: "preview-run",
    title: "Agent run recorded",
    body: "See what the agent did in Activity.",
    href: "/activity",
    createdAt: "2026-11-09T18:22:00.000Z",
    kind: "activity",
    preview: true,
  },
  {
    id: "preview-telegram",
    title: "Telegram",
    body: "Connection status is available under Connections.",
    href: "/connections/telegram",
    createdAt: "2026-11-09T16:04:00.000Z",
    kind: "connection",
    preview: true,
  },
  {
    id: "preview-google",
    title: "Google",
    body: "Gmail, Calendar, and Drive previews live here.",
    href: "/connections/google",
    createdAt: "2026-11-09T14:41:00.000Z",
    kind: "connection",
    preview: true,
  },
  {
    id: "preview-linkedin",
    title: "LinkedIn",
    body: "Drafts and channel status are on this page.",
    href: "/connections/linkedin",
    createdAt: "2026-11-09T11:18:00.000Z",
    kind: "connection",
    preview: true,
  },
  {
    id: "preview-facebook",
    title: "Facebook",
    body: "Channel preview is ready to open.",
    href: "/connections/facebook",
    createdAt: "2026-11-08T19:55:00.000Z",
    kind: "connection",
    preview: true,
  },
  {
    id: "preview-connections",
    title: "Connections",
    body: "Browse every channel from the directory.",
    href: "/connections",
    createdAt: "2026-11-08T15:12:00.000Z",
    kind: "connection",
    preview: true,
  },
  {
    id: "preview-activity-older",
    title: "Earlier activity",
    body: "Older audit entries stay on Activity.",
    href: "/activity",
    createdAt: "2026-11-08T10:03:00.000Z",
    kind: "activity",
    preview: true,
  },
  {
    id: "preview-task-followup",
    title: "Task follow-up",
    body: "Pending work stays on Tasks.",
    href: "/tasks",
    createdAt: "2026-11-07T17:28:00.000Z",
    kind: "approval",
    preview: true,
  },
  {
    id: "preview-calendar",
    title: "Google Calendar",
    body: "Calendar preview is under Google connections.",
    href: "/connections/google",
    createdAt: "2026-11-07T09:46:00.000Z",
    kind: "connection",
    preview: true,
  },
];

export function notificationsWithApprovals(approvalCount: number | null): ShellNotification[] {
  if (!approvalCount || approvalCount < 1) {
    return mockNotifications;
  }

  const live: ShellNotification = {
    id: "live-approvals",
    title: approvalCount === 1 ? "1 approval waiting" : `${approvalCount} approvals waiting`,
    body: "Open Tasks to approve or reject the pending action.",
    href: "/tasks",
    createdAt: new Date().toISOString(),
    kind: "approval",
    preview: false,
  };

  return [live, ...mockNotifications];
}
