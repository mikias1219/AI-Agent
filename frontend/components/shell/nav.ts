/**
 * Sidebar IA (redesign: agent in every module). Pages are grouped by how often they are used:
 * Daily (open every day) and Grow (learning and notes). Chat is not a destination any more:
 * each module has its own agent panel; /chat stays reachable from the agent panel and Ctrl K.
 */

export const NAV_GROUPS = [
  {
    id: "daily",
    label: "Daily",
    items: [
      { href: "/", label: "Today", hint: "Your day" },
      {
        href: "/tasks",
        label: "Plan",
        hint: "Tasks, habits, goals, calendar",
        badgeKey: "tasksLeft",
        match: ["/tasks", "/habits", "/projects", "/goals", "/time", "/calendar", "/review"],
      },
      { href: "/money", label: "Money", hint: "Income, spending, budgets", match: ["/money"] },
      {
        href: "/inbox",
        label: "Needs you",
        badgeKey: "needsYou",
        hint: "Approvals and mail",
        match: ["/inbox", "/mail"],
      },
    ],
  },
  {
    id: "grow",
    label: "Grow",
    items: [
      {
        href: "/learn",
        label: "Learn",
        hint: "Words and reading",
        badgeKey: "wordsDue",
        match: ["/learn"],
      },
      { href: "/library", label: "Library", hint: "Notes, diary, files", match: ["/library"] },
    ],
  },
  {
    id: "footer",
    label: "",
    items: [
      {
        href: "/agent",
        label: "Agent",
        hint: "Memory, routines, activity, connections",
        match: [
          "/agent",
          "/memory",
          "/routines",
          "/activity",
          "/automations",
          "/connections",
          "/chat",
        ],
      },
      { href: "/settings", label: "Settings", hint: "Profile and preferences" },
    ],
  },
] as const;

export type NavGroup = (typeof NAV_GROUPS)[number];
export type NavItem = NavGroup["items"][number];
export type NavHref = NavItem["href"];
export type NavBadgeKey = "needsYou" | "tasksLeft" | "wordsDue";
export type NavCounts = Partial<Record<NavBadgeKey, number | null>>;

export const NAV_ITEMS: readonly NavItem[] = NAV_GROUPS.flatMap(
  (group) => [...group.items] as NavItem[],
);

/** Mobile bottom bar: Today, Plan, a central + (quick add), Money, Needs you. */
export const BOTTOM_NAV = [
  { href: "/", label: "Today" },
  { href: "/tasks", label: "Plan" },
  { href: "/money", label: "Money" },
  { href: "/inbox", label: "Needs you" },
] as const;

/** Reached from the header menu on phones (the bottom bar has no room). */
export const MORE_NAV = [
  { href: "/learn", label: "Learn", hint: "Words and reading" },
  { href: "/library", label: "Library", hint: "Notes, diary, files" },
  { href: "/agent", label: "Agent", hint: "Memory, routines, activity" },
  { href: "/settings", label: "Settings", hint: "Profile and preferences" },
] as const;

/** Paths that still exist but live under a hub (not top-level nav). */
export const HUB_ALIASES: Record<string, string> = {
  "/habits": "/tasks",
  "/projects": "/tasks",
  "/time": "/tasks",
  "/review": "/tasks",
  "/goals": "/tasks",
  "/calendar": "/tasks",
  "/mail": "/inbox",
  "/memory": "/agent",
  "/routines": "/agent",
  "/activity": "/agent",
  "/automations": "/agent",
  "/connections": "/agent",
  "/help": "/settings",
};

export function isNavActive(pathname: string, href: string): boolean {
  const item = NAV_ITEMS.find((row) => row.href === href);
  const aliases =
    item && "match" in item && item.match ? (item.match as readonly string[]) : [href];
  return aliases.some((path) => {
    if (path === "/") return pathname === "/";
    return pathname === path || pathname.startsWith(`${path}/`);
  });
}

export function titleForPath(pathname: string): string {
  if (pathname === "/mail" || pathname.startsWith("/mail/")) return "Needs you";
  if (pathname === "/goals" || pathname.startsWith("/goals/")) return "Plan";
  if (pathname === "/habits" || pathname.startsWith("/habits/")) return "Plan";
  if (pathname === "/projects" || pathname.startsWith("/projects/")) return "Plan";
  if (pathname === "/time" || pathname.startsWith("/time/")) return "Plan";
  if (pathname === "/review" || pathname.startsWith("/review/")) return "Plan";
  if (pathname === "/calendar" || pathname.startsWith("/calendar/")) return "Plan";
  if (
    pathname.startsWith("/agent") ||
    pathname.startsWith("/memory") ||
    pathname.startsWith("/routines") ||
    pathname.startsWith("/activity") ||
    pathname.startsWith("/automations") ||
    pathname.startsWith("/connections")
  ) {
    return "Agent";
  }
  if (pathname === "/chat" || pathname.startsWith("/chat/")) {
    return "Conversations";
  }
  if (pathname === "/help" || pathname.startsWith("/help/")) return "Help";
  const match = NAV_ITEMS.find((item) => isNavActive(pathname, item.href));
  return match?.label ?? "Today";
}

/** Kept for callers; purpose lines belong in empty states, not the sticky header. */
export function pagePurpose(_pathname: string): string {
  return "";
}
