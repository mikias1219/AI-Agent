"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { focusFirst, trapFocus } from "@/lib/focus-trap";
import { IconButton } from "./icon-button";

export type DrawerProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
};

export function Drawer({ open, onClose, title, children }: DrawerProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (panel) focusFirst(panel);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (panel) trapFocus(panel, e);
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
      previousFocus.current?.focus();
    };
  }, [open, onClose]);

  return (
    <>
      <button
        type="button"
        aria-hidden={!open}
        tabIndex={open ? 0 : -1}
        className={`fixed inset-0 z-40 bg-[var(--ink)]/30 transition-opacity duration-200 motion-reduce:transition-none ${open ? "opacity-100" : "pointer-events-none opacity-0"}`}
        aria-label="Close drawer"
        onClick={onClose}
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal={open}
        aria-labelledby={titleId}
        aria-hidden={!open}
        inert={!open}
        className={`fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[var(--drawer-width)] flex-col border-l border-[var(--border)] bg-[var(--surface)] shadow-lg transition-transform duration-200 ease-out motion-reduce:transition-none sm:max-w-md ${
          open ? "translate-x-0" : "invisible translate-x-full pointer-events-none"
        }`}
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] px-4 py-3">
          <h2
            id={titleId}
            className="text-[length:var(--text-title)] font-semibold text-[var(--ink)]"
          >
            {title}
          </h2>
          <IconButton label="Close" size="sm" onClick={onClose}>
            <X className="h-4 w-4" aria-hidden />
          </IconButton>
        </div>
        <div className="flex-1 overflow-y-auto px-4 py-4">{children}</div>
      </aside>
    </>
  );
}
