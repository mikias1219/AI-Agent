export const NAV_ITEMS = [
  { href: "/", label: "Overview" },
  { href: "/chat", label: "Chat" },
  { href: "/tasks", label: "Tasks" },
  { href: "/activity", label: "Activity" },
  { href: "/connections", label: "Connections" },
  { href: "/settings", label: "Settings" },
] as const;

export type NavHref = (typeof NAV_ITEMS)[number]["href"];

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function titleForPath(pathname: string): string {
  const match = NAV_ITEMS.find((item) => isNavActive(pathname, item.href));
  return match?.label ?? "Overview";
}
