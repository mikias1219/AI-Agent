"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { LogOut, Settings, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { displayName } from "@/lib/auth/session";
import type { User } from "@/lib/api/types";

export type ProfileMenuProps = {
  user: User | null;
  open: boolean;
  onClose: () => void;
  onSignOut: () => Promise<void>;
};

export function ProfileMenu({ user, open, onClose, onSignOut }: ProfileMenuProps) {
  const router = useRouter();
  const panelRef = useRef<HTMLDivElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const name = displayName(user);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open) {
      panelRef.current?.querySelector<HTMLElement>("a, button")?.focus();
    }
  }, [open]);

  if (!open) return null;

  async function signOut() {
    setBusy(true);
    setError(null);
    try {
      await onSignOut();
      router.replace("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign out.");
      setBusy(false);
    }
  }

  return (
    <div
      ref={panelRef}
      role="menu"
      aria-label="Profile"
      className="absolute top-[calc(100%+0.5rem)] right-0 z-30 w-60 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-2 shadow-lg"
    >
      <div className="border-b border-[var(--border)] px-2 py-2">
        <p className="truncate text-sm font-medium text-[var(--ink)]">{name}</p>
        {user?.email ? <p className="truncate text-xs text-[var(--muted)]">{user.email}</p> : null}
      </div>
      <div className="flex flex-col py-1">
        <MenuLink href="/settings?section=account" onClick={onClose}>
          <UserRound className="h-4 w-4" aria-hidden />
          Account
        </MenuLink>
        <MenuLink href="/settings" onClick={onClose}>
          <Settings className="h-4 w-4" aria-hidden />
          Settings
        </MenuLink>
      </div>
      <Button
        variant="ghost"
        role="menuitem"
        className="w-full justify-start px-2"
        loading={busy}
        onClick={() => void signOut()}
      >
        <LogOut className="h-4 w-4" aria-hidden />
        Sign out
      </Button>
      {error ? <p className="px-2 pt-1 text-xs text-[var(--danger)]">{error}</p> : null}
    </div>
  );
}

function MenuLink({
  href,
  onClick,
  children,
}: {
  href: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <Link
      href={href}
      role="menuitem"
      onClick={onClick}
      className="flex items-center gap-2 rounded-[var(--radius)] px-2 py-2 text-sm text-[var(--ink)] hover:bg-[var(--canvas)]"
    >
      {children}
    </Link>
  );
}
