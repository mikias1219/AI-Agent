"use client";

import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { X } from "lucide-react";
import { IconButton } from "./icon-button";

export type ToastTone = "neutral" | "success" | "warning" | "danger";

export type ToastAction = {
  label: string;
  onClick: () => void | Promise<void>;
};

type ToastItem = {
  id: string;
  message: string;
  tone: ToastTone;
  action?: ToastAction;
};

type ToastOptions = {
  tone?: ToastTone;
  action?: ToastAction;
  durationMs?: number;
};

type ToastContextValue = {
  toast: (message: string, toneOrOptions?: ToastTone | ToastOptions) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const toneBorder: Record<ToastTone, string> = {
  neutral: "border-l-[var(--border-strong)]",
  success: "border-l-[var(--success)]",
  warning: "border-l-[var(--warning)]",
  danger: "border-l-[var(--danger)]",
};

function resolveOptions(
  toneOrOptions?: ToastTone | ToastOptions,
): Required<Pick<ToastOptions, "tone" | "durationMs">> & Pick<ToastOptions, "action"> {
  if (!toneOrOptions || typeof toneOrOptions === "string") {
    return { tone: toneOrOptions ?? "neutral", durationMs: 4500 };
  }
  return {
    tone: toneOrOptions.tone ?? "neutral",
    action: toneOrOptions.action,
    durationMs: toneOrOptions.durationMs ?? (toneOrOptions.action ? 10_000 : 4500),
  };
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setItems((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback(
    (message: string, toneOrOptions?: ToastTone | ToastOptions) => {
      const opts = resolveOptions(toneOrOptions);
      const id = crypto.randomUUID();
      setItems((prev) => [...prev, { id, message, tone: opts.tone, action: opts.action }]);
      window.setTimeout(() => dismiss(id), opts.durationMs);
    },
    [dismiss],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed right-4 bottom-[calc(var(--bottom-nav-height)+env(safe-area-inset-bottom)+0.75rem)] left-4 z-[100] flex flex-col gap-2 sm:left-auto sm:max-w-sm md:bottom-4"
        aria-live="polite"
      >
        {items.map((item) => (
          <div
            key={item.id}
            className={`aura-pop pointer-events-auto flex items-start gap-2 rounded-[var(--radius)] border border-[var(--border)] border-l-4 bg-[var(--surface-raised)] py-2.5 pr-2 pl-3.5 text-[length:var(--text-body)] leading-[var(--leading-body)] text-[var(--ink)] shadow-[var(--shadow-2)] ${toneBorder[item.tone]}`}
          >
            <div className="flex flex-1 flex-col gap-1">
              <p className="py-1">{item.message}</p>
              {item.action ? (
                <button
                  type="button"
                  className="self-start text-[length:var(--text-caption)] font-semibold text-[var(--accent-strong)] underline-offset-2 hover:underline"
                  onClick={() => {
                    void item.action?.onClick();
                    dismiss(item.id);
                  }}
                >
                  {item.action.label}
                </button>
              ) : null}
            </div>
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
