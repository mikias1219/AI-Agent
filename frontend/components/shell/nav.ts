/** Lean shell destinations — related surfaces share one primary item. */

export const NAV_GROUPS = [
  {
    id: "primary",
    items: [
      { href: "/", label: "Today", hint: "Day overview" },
      { href: "/chat", label: "Chat", hint: "Talk to AURA" },
      { href: "/inbox", label: "Needs you", badgeKey: "needsYou", hint: "Approvals" },
    ],
  },
  {
    id: "spaces",
    label: "Spaces",
    items: [
      { href: "/tasks", label: "Work", hint: "Tasks & goals", match: ["/tasks", "/goals"] },
      {
        href: "/calendar",
        label: "Schedule",
        hint: "Calendar & mail",
        match: ["/calendar", "/mail"],
      },
      { href: "/memory", label: "Memory", hint: "What AURA knows" },
      {
        href: "/routines",
        label: "Agent",
        hint: "Routines & activity",
        match: ["/routines", "/activity", "/automations"],
      },
    ],
  },
  {
    id: "footer",
    items: [
      { href: "/connections", label: "Connections" },
      { href: "/settings", label: "Settings" },
    ],
  },
] as const;

export type NavGroup = (typeof NAV_GROUPS)[number];
export type NavItem = NavGroup["items"][number];
export type NavHref = NavItem["href"];
export type NavBadgeKey = "needsYou";

/** Flat list of every primary nav destination, in display order. */
export const NAV_ITEMS: readonly NavItem[] = NAV_GROUPS.flatMap(
  (group) => [...group.items] as NavItem[],
);

/** Paths that still exist but live under a hub (not top-level nav). */
export const HUB_ALIASES: Record<string, string> = {
  "/goals": "/tasks",
  "/mail": "/calendar",
  "/activity": "/routines",
  "/automations": "/routines",
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
  if (pathname === "/goals" || pathname.startsWith("/goals/")) return "Work";
  if (pathname === "/mail" || pathname.startsWith("/mail/")) return "Schedule";
  if (
    pathname === "/activity" ||
    pathname.startsWith("/activity/") ||
    pathname === "/automations" ||
    pathname.startsWith("/automations/")
  ) {
    return "Agent";
  }
  if (pathname === "/help" || pathname.startsWith("/help/")) return "Settings";
  const match = NAV_ITEMS.find((item) => isNavActive(pathname, item.href));
  return match?.label ?? "Today";
}

export function pagePurpose(pathname: string): string {
  if (pathname === "/" || pathname === "") return "Your day at a glance";
  if (pathname.startsWith("/chat")) return "Ask AURA to act";
  if (pathname.startsWith("/inbox")) return "Decisions waiting on you";
  if (pathname.startsWith("/tasks") || pathname.startsWith("/goals")) {
    return "Tasks and longer outcomes";
  }
  if (pathname.startsWith("/calendar") || pathname.startsWith("/mail")) {
    return "Calendar and inbox";
  }
  if (pathname.startsWith("/memory")) return "What AURA remembers";
  if (
    pathname.startsWith("/routines") ||
    pathname.startsWith("/activity") ||
    pathname.startsWith("/automations")
  ) {
    return "Scheduled work and history";
  }
  if (pathname.startsWith("/connections")) return "Link Google, Telegram, MCP";
  if (pathname.startsWith("/settings") || pathname.startsWith("/help")) {
    return "Preferences and help";
  }
  return "";
}
