"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Bell, Menu, Search } from "lucide-react";
import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { displayName } from "@/lib/auth/session";
import type { User } from "@/lib/api/types";
import { titleForPath } from "./nav";
import { ProfileMenu } from "./profile-menu";

export type AppHeaderProps = {
  user: User | null;
  approvalCount: number | null;
  notificationsOpen: boolean;
  sidebarOpen: boolean;
  onOpenSidebar: () => void;
  onOpenNotifications: () => void;
  onSignOut: () => Promise<void>;
};

export function AppHeader({
  user,
  approvalCount,
  notificationsOpen,
  sidebarOpen,
  onOpenSidebar,
  onOpenNotifications,
  onSignOut,
}: AppHeaderProps) {
  const pathname = usePathname();
  const title = titleForPath(pathname);
  const name = displayName(user);
  const menuRef = useRef<HTMLDivElement>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const pending = approvalCount && approvalCount > 0 ? approvalCount : 0;
  const bellLabel =
    pending > 0
      ? `Notifications, ${pending} pending ${pending === 1 ? "approval" : "approvals"}`
      : "Notifications";

  useEffect(() => {
    setMenuOpen(false);
  }, [pathname, notificationsOpen]);

  useEffect(() => {
    if (!menuOpen) return;
    function onPointer(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [menuOpen]);

  return (
    <header className="sticky top-0 z-20 border-b border-[var(--border)] bg-[var(--surface)]/95 backdrop-blur">
      <div className="flex items-center gap-3 px-4 py-3">
        <IconButton
          label="Open menu"
          className="md:hidden"
          aria-expanded={sidebarOpen}
          aria-controls="app-sidebar"
          onClick={onOpenSidebar}
        >
          <Menu className="h-4 w-4" aria-hidden />
        </IconButton>
        <h1
          className="min-w-0 flex-1 truncate text-xl font-semibold tracking-tight text-[var(--ink)] sm:flex-none"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {title}
        </h1>
        <SearchField className="mx-auto hidden w-full max-w-sm md:block" />
        <div className="ml-auto flex items-center gap-2">
          <span className="relative inline-flex">
            <IconButton
              label={bellLabel}
              aria-expanded={notificationsOpen}
              aria-haspopup="dialog"
              onClick={onOpenNotifications}
            >
              <Bell className="h-4 w-4" aria-hidden />
            </IconButton>
            {pending > 0 ? (
              <Badge
                tone="warning"
                className="pointer-events-none absolute -top-2 -right-2 min-w-5 justify-center px-1"
              >
                {pending > 9 ? "9+" : pending}
              </Badge>
            ) : null}
          </span>
          <div className="relative" ref={menuRef}>
            <button
              type="button"
              className="rounded-full"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
              aria-label="Open profile menu"
              onClick={() => setMenuOpen((open) => !open)}
            >
              <Avatar name={name} size="sm" />
            </button>
            <ProfileMenu
              user={user}
              open={menuOpen}
              onClose={() => setMenuOpen(false)}
              onSignOut={onSignOut}
            />
          </div>
        </div>
      </div>
      <div className="px-4 pb-3 md:hidden">
        <SearchField />
      </div>
    </header>
  );
}

function SearchField({ className = "" }: { className?: string }) {
  return (
    <div className={`relative ${className}`}>
      <Search
        className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-[var(--muted)]"
        aria-hidden
      />
      <Input
        readOnly
        aria-disabled="true"
        tabIndex={-1}
        placeholder="Search soon"
        aria-label="Search"
        className="cursor-default pl-9"
      />
    </div>
  );
}
