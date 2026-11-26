/** Six destinations (IA v4). Existing URLs stay canonical; hubs group related screens. */

export const NAV_GROUPS = [
  {
    id: "primary",
    items: [
      { href: "/", label: "Today", hint: "Your day" },
      { href: "/chat", label: "Chat", hint: "Ask Compass" },
      { href: "/library", label: "Library", hint: "Notes, diary, files", match: ["/library"] },
      { href: "/learn", label: "Learn", hint: "Words and reading", match: ["/learn"] },
      {
        href: "/tasks",
        label: "Plan",
        hint: "Tasks, habits, goals, calendar",
        match: ["/tasks", "/habits", "/projects", "/goals", "/time", "/calendar", "/review"],
      },
      { href: "/money", label: "Money", hint: "Spending, budgets, bills", match: ["/money"] },
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
    id: "footer",
    items: [
      {
        href: "/agent",
        label: "Agent",
        hint: "Memory, routines, activity, connections",
        match: ["/agent", "/memory", "/routines", "/activity", "/automations", "/connections"],
      },
      { href: "/settings", label: "Settings", hint: "Profile and preferences" },
    ],
  },
] as const;

export type NavGroup = (typeof NAV_GROUPS)[number];
export type NavItem = NavGroup["items"][number];
export type NavHref = NavItem["href"];
export type NavBadgeKey = "needsYou";

export const NAV_ITEMS: readonly NavItem[] = NAV_GROUPS.flatMap(
  (group) => [...group.items] as NavItem[],
);

/** Mobile bottom bar: four destinations, then More. */
export const BOTTOM_NAV = [
  { href: "/", label: "Today" },
  { href: "/chat", label: "Chat" },
  { href: "/library", label: "Library" },
  { href: "/learn", label: "Learn" },
] as const;

/** Listed in the More sheet on phones. */
export const MORE_NAV = [
  { href: "/tasks", label: "Plan", hint: "Tasks, habits, goals, calendar" },
  { href: "/money", label: "Money", hint: "Spending, budgets, bills" },
  { href: "/inbox", label: "Needs you", hint: "Approvals and mail", badgeKey: "needsYou" as const },
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
  if (pathname === "/help" || pathname.startsWith("/help/")) return "Help";
  const match = NAV_ITEMS.find((item) => isNavActive(pathname, item.href));
  return match?.label ?? "Today";
}

/** Kept for callers; purpose lines belong in empty states, not the sticky header. */
export function pagePurpose(_pathname: string): string {
  return "";
}
