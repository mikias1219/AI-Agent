"use client";

import { quickExpense } from "@/lib/api/finance";
import { formatMoney, parseAmount } from "@/lib/money";
import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { focusFirst, trapFocus } from "@/lib/focus-trap";
import { createTask } from "@/lib/api/tasks";
import { apiErrorMessage } from "@/lib/api/client";
import { useToast } from "@/components/ui/toast";

export type CommandPaletteProps = {
  open: boolean;
  onClose: () => void;
  onOpenQuickAsk: () => void;
};

type Command = {
  id: string;
  label: string;
  hint?: string;
  keywords?: string;
  run: () => void | Promise<void>;
};

/** Ctrl/Cmd+K palette: go to a place, ask in Chat, or create a task. */
export function CommandPalette({ open, onClose, onOpenQuickAsk }: CommandPaletteProps) {
  const router = useRouter();
  const { toast } = useToast();
  const panelRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commands = useMemo<Command[]>(() => {
    const go = (href: string, label: string): Command => ({
      id: `go-${href}`,
      label: `Go to ${label}`,
      hint: href === "/" ? "Today" : href,
      keywords: label,
      run: () => {
        router.push(href);
        onClose();
      },
    });
    return [
      {
        id: "ask-chat",
        label: query.trim() ? `Ask in Chat: “${query.trim()}”` : "Ask in Chat…",
        hint: "Opens Chat and sends",
        keywords: "ask chat",
        run: () => {
          const text = query.trim();
          if (text) {
            router.push(`/chat?q=${encodeURIComponent(text)}`);
          } else {
            router.push("/chat");
          }
          onClose();
        },
      },
      {
        id: "ask-quick",
        label: "Quick ask",
        hint: "Drawer",
        keywords: "ask quick",
        run: () => {
          onClose();
          onOpenQuickAsk();
        },
      },
      {
        id: "new-task",
        label: query.trim() ? `New task: “${query.trim()}”` : "New task…",
        hint: "Creates immediately when you typed a title",
        keywords: "task create",
        run: async () => {
          const title = query.trim();
          if (!title) {
            router.push("/tasks");
            onClose();
            return;
          }
          setBusy(true);
          setError(null);
          try {
            await createTask({ title });
            toast(`Created task “${title}”`, "success");
            router.push("/tasks");
            onClose();
          } catch (err) {
            setError(apiErrorMessage(err));
          } finally {
            setBusy(false);
          }
        },
      },
      {
        id: "new-expense",
        label: parseAmount(query) !== null ? `Add expense: ${query.trim()}` : "Add expense…",
        hint: "Type an amount to save it now",
        keywords: "money expense spend cost pay",
        run: async () => {
          const amount = parseAmount(query);
          if (amount === null) {
            router.push("/money");
            onClose();
            return;
          }
          setBusy(true);
          setError(null);
          try {
            await quickExpense(amount);
            toast(`Saved ${formatMoney(Math.round(amount * 100))}`, "success");
            onClose();
          } catch (err) {
            setError(apiErrorMessage(err));
          } finally {
            setBusy(false);
          }
        },
      },
      {
        id: "new-note",
        label: "New note",
        hint: "Library",
        keywords: "note write library",
        run: () => {
          router.push("/library?new=note");
          onClose();
        },
      },
      {
        id: "new-diary",
        label: "Write diary",
        hint: "Today's entry",
        keywords: "diary journal write entry",
        run: () => {
          router.push("/library?new=diary");
          onClose();
        },
      },
      {
        id: "add-words",
        label: "Add words",
        hint: "Ask Compass to teach me 5 words",
        keywords: "words learn vocabulary teach",
        run: () => {
          router.push(`/chat?q=${encodeURIComponent("Teach me 5 English words")}`);
          onClose();
        },
      },
      {
        id: "log-reading",
        label: "Log reading",
        hint: "Learn",
        keywords: "reading bible passage log",
        run: () => {
          router.push("/learn?tab=reading");
          onClose();
        },
      },
      {
        id: "upload-file",
        label: "Upload file",
        hint: "Library",
        keywords: "file upload image document",
        run: () => {
          router.push("/library?tab=files");
          onClose();
        },
      },
      go("/", "Today"),
      go("/chat", "Chat"),
      go("/library", "Library"),
      go("/learn", "Learn"),
      go("/tasks", "Plan"),
      go("/habits", "Habits"),
      go("/money", "Money"),
      go("/inbox", "Needs you"),
      go("/agent", "Agent"),
      go("/settings", "Settings"),
      go("/help", "Help"),
    ];
  }, [query, router, onClose, onOpenQuickAsk, toast]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter((command) => {
      const hay = `${command.label} ${command.hint ?? ""} ${command.keywords ?? ""}`.toLowerCase();
      return hay.includes(q) || command.id.startsWith("ask") || command.id === "new-task";
    });
  }, [commands, query]);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setActive(0);
      setError(null);
      setBusy(false);
      return;
    }
    const id = window.setTimeout(() => inputRef.current?.focus(), 20);
    if (panelRef.current) focusFirst(panelRef.current);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const panel = panelRef.current;
    function onKey(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") onClose();
      if (panel) trapFocus(panel, event);
    }
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  if (!open) return null;

  const selected = filtered[Math.min(active, Math.max(filtered.length - 1, 0))];

  function onInputKey(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((index) => Math.min(index + 1, filtered.length - 1));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((index) => Math.max(index - 1, 0));
    } else if (event.key === "Enter") {
      event.preventDefault();
      if (selected && !busy) void selected.run();
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (selected && !busy) void selected.run();
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-start justify-center px-4 pt-[12vh]">
      <button
        type="button"
        className="compass-fade absolute inset-0 bg-[var(--overlay)] backdrop-blur-[2px]"
        aria-label="Close command palette"
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        className="compass-pop relative z-10 flex w-full max-w-xl flex-col overflow-hidden rounded-[var(--radius-lg)] border border-[var(--border)] bg-[var(--surface-raised)] shadow-[var(--shadow-3)]"
      >
        <form onSubmit={onSubmit} className="border-b border-[var(--border)]">
          <label className="sr-only" htmlFor="command-palette-input">
            Command
          </label>
          <input
            ref={inputRef}
            id="command-palette-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={onInputKey}
            placeholder="Ask, write a note, or go to…"
            disabled={busy}
            className="w-full bg-transparent px-4 py-4 text-[length:var(--text-title)] text-[var(--ink)] outline-none placeholder:text-[var(--muted)]"
          />
        </form>
        <ul className="max-h-72 overflow-y-auto p-2" role="listbox" aria-label="Commands">
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-[length:var(--text-body)] text-[var(--muted)]">
              No matches
            </li>
          ) : (
            filtered.map((command, index) => {
              const isActive = index === active;
              return (
                <li key={command.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={isActive}
                    disabled={busy}
                    className={`flex w-full items-center justify-between gap-3 min-h-10 rounded-[var(--radius-sm)] px-3 py-2 text-left text-[length:var(--text-body)] transition-colors duration-100 ${
                      isActive
                        ? "bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                        : "text-[var(--ink)] hover:bg-[var(--hover)]"
                    }`}
                    onMouseEnter={() => setActive(index)}
                    onClick={() => void command.run()}
                  >
                    <span className="truncate">{command.label}</span>
                    {command.hint ? (
                      <span className="shrink-0 text-[length:var(--text-caption)] text-[var(--muted)]">
                        {command.hint}
                      </span>
                    ) : null}
                  </button>
                </li>
              );
            })
          )}
        </ul>
        {error ? (
          <p
            className="border-t border-[var(--border)] px-4 py-2 text-[length:var(--text-body)] text-[var(--danger)]"
            role="alert"
          >
            {error}
          </p>
        ) : null}
      </div>
    </div>
  );
}
