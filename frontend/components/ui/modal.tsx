"use client";

import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";
import { focusFirst, trapFocus } from "@/lib/focus-trap";
import { IconButton } from "./icon-button";

export type ModalProps = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
};

export function Modal({ open, onClose, title, children }: ModalProps) {
  const titleId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);
  // Parents usually pass a new onClose on every render. Keeping it in a ref means typing in
  // a field (which re-renders the parent) does not re-run the open effect and steal focus.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    if (panel) focusFirst(panel);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseRef.current();
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
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="compass-fade absolute inset-0 bg-[var(--overlay)] backdrop-blur-[2px]"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="compass-pop relative z-10 max-h-[calc(100dvh-2rem)] w-full max-w-lg overflow-y-auto rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface-raised)] shadow-[var(--shadow-3)]"
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-3.5">
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
        <div className="px-5 py-5">{children}</div>
      </div>
    </div>
  );
}
