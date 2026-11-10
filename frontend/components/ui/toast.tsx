"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { IconButton } from "./icon-button";

export type ToastTone = "neutral" | "success" | "warning" | "danger";

type ToastItem = {
  id: string;
  message: string;
  tone: ToastTone;
};

type ToastContextValue = {
  toast: (message: string, tone?: ToastTone) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const toneBorder: Record<ToastTone, string> = {
  neutral: "border-[var(--border)]",
  success: "border-[var(--success)]",
  warning: "border-[var(--warning)]",
  danger: "border-[var(--danger)]",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, tone: ToastTone = "neutral") => {
      const id = crypto.randomUUID();
      setItems((prev) => [...prev, { id, message, tone }]);
      window.setTimeout(() => dismiss(id), 4500);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed right-4 bottom-4 z-[100] flex max-w-sm flex-col gap-2"
        aria-live="polite"
      >
        {items.map((item) => (
          <div
            key={item.id}
            className={`pointer-events-auto flex items-start gap-2 rounded-[var(--radius)] border bg-[var(--surface)] px-3 py-2 text-sm text-[var(--ink)] shadow-md ${toneBorder[item.tone]}`}
          >
            <p className="flex-1">{item.message}</p>
            <IconButton label="Dismiss" size="sm" onClick={() => dismiss(item.id)}>
              <X className="h-4 w-4" aria-hidden />
            </IconButton>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast must be used within ToastProvider");
  }
  return ctx;
}
