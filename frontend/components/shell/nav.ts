export const NAV_GROUPS = [
  {
    id: "primary",
    items: [
      { href: "/", label: "Today" },
      { href: "/chat", label: "Chat" },
      { href: "/inbox", label: "Inbox", badgeKey: "needsYou" },
    ],
  },
  {
    id: "my-work",
    label: "My work",
    items: [
      { href: "/tasks", label: "Tasks" },
      { href: "/goals", label: "Goals" },
      { href: "/calendar", label: "Calendar" },
      { href: "/mail", label: "Mail" },
    ],
  },
  {
    id: "aura",
    label: "AURA",
    items: [
      { href: "/memory", label: "Memory" },
      { href: "/routines", label: "Routines" },
      { href: "/activity", label: "Activity" },
    ],
  },
  {
    id: "footer",
    items: [
      { href: "/connections", label: "Connections" },
      { href: "/settings", label: "Settings" },
      { href: "/help", label: "Help" },
    ],
  },
] as const;

export type NavGroup = (typeof NAV_GROUPS)[number];
export type NavItem = NavGroup["items"][number];
export type NavHref = NavItem["href"];
export type NavBadgeKey = "needsYou";

/** Flat list of every nav destination, in display order. */
export const NAV_ITEMS: readonly NavItem[] = NAV_GROUPS.flatMap(
  (group) => [...group.items] as NavItem[],
);

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function titleForPath(pathname: string): string {
  if (pathname === "/automations" || pathname.startsWith("/automations/")) return "Routines";
  const match = NAV_ITEMS.find((item) => isNavActive(pathname, item.href));
  return match?.label ?? "Today";
}
