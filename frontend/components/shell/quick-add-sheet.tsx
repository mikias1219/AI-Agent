"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Modal } from "@/components/ui/modal";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { createTransaction } from "@/lib/api/finance";
import { createNote, type Mood } from "@/lib/api/notes";
import { createTask } from "@/lib/api/tasks";
import { parseAmount } from "@/lib/money";

export type QuickKind = "expense" | "income" | "task" | "note" | "mood";

export const QUICK_KINDS: { id: QuickKind; label: string }[] = [
  { id: "expense", label: "Expense" },
  { id: "income", label: "Income" },
  { id: "task", label: "Task" },
  { id: "note", label: "Note" },
  { id: "mood", label: "Mood" },
];

const MOODS: { id: Mood; label: string }[] = [
  { id: "great", label: "Great" },
  { id: "good", label: "Good" },
  { id: "okay", label: "Okay" },
  { id: "low", label: "Low" },
  { id: "bad", label: "Bad" },
];

/**
 * The one place to add anything. Same sheet everywhere, so you never hunt for where to add.
 * Each kind shows only the fields it needs (amount + Save for money).
 */
export function QuickAddSheet({
  open,
  onClose,
  initial = "expense",
}: {
  open: boolean;
  onClose: () => void;
  initial?: QuickKind;
}) {
  const { toast } = useToast();
  const [kind, setKind] = useState<QuickKind>(initial);
  const [text, setText] = useState("");
  const [amount, setAmount] = useState("");
  const [mood, setMood] = useState<Mood>("good");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const money = kind === "expense" || kind === "income";

  async function save() {
    setError("");
    setBusy(true);
    try {
      if (money) {
        const value = parseAmount(amount);
        if (value === null) throw new Error("Enter an amount such as 250 or 1,250.50.");
        await createTransaction({ kind, amount: String(value), merchant: text.trim() });
        toast(`${kind === "income" ? "Income" : "Expense"} saved`, "success");
      } else if (kind === "task") {
        if (text.trim().length < 3) throw new Error("Give the task a few words.");
        await createTask({ title: text.trim() });
        toast("Task added to your plan", "success");
      } else if (kind === "note") {
        if (!text.trim()) throw new Error("Write something first.");
        await createNote({ kind: "note", body: text.trim() });
        toast("Note saved", "success");
      } else {
        await createNote({ kind: "diary", body: text.trim() || "Mood check-in", mood });
        toast("Mood saved to your diary", "success");
      }
      setText("");
      setAmount("");
      onClose();
      window.dispatchEvent(new Event("compass:data-changed"));
    } catch (err) {
      setError(err instanceof Error && !("status" in err) ? err.message : apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Add">
      <div className="flex flex-col gap-4">
        <div role="group" aria-label="What to add" className="flex flex-wrap gap-1.5">
          {QUICK_KINDS.map((k) => (
            <button
              key={k.id}
              type="button"
              aria-pressed={kind === k.id}
              onClick={() => setKind(k.id)}
              className={`min-h-11 rounded-full border px-3.5 text-sm transition focus-visible:outline-2 focus-visible:outline-[var(--accent)] ${
                kind === k.id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)] font-medium text-[var(--accent-strong)]"
                  : "border-[var(--border)] text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
            >
              {k.label}
            </button>
          ))}
        </div>
        {money ? (
          <Field label="Amount (ETB)" htmlFor="qa-amount">
            <Input
              id="qa-amount"
              inputMode="decimal"
              autoFocus
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              placeholder="250"
            />
          </Field>
        ) : null}
        {kind === "mood" ? (
          <div role="group" aria-label="Mood" className="flex flex-wrap gap-1.5">
            {MOODS.map((m) => (
              <button
                key={m.id}
                type="button"
                aria-pressed={mood === m.id}
                onClick={() => setMood(m.id)}
                className={`min-h-11 rounded-full border px-3.5 text-sm ${
                  mood === m.id
                    ? "border-[var(--accent)] bg-[var(--accent-soft)] font-medium"
                    : "border-[var(--border)] text-[var(--muted)]"
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>
        ) : null}
        <Field
          label={
            money
              ? "What for (optional)"
              : kind === "task"
                ? "Task"
                : kind === "note"
                  ? "Note"
                  : "One line (optional)"
          }
          htmlFor="qa-text"
        >
          <Input
            id="qa-text"
            autoFocus={!money}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void save();
            }}
          />
        </Field>
        {error ? (
          <p role="alert" className="text-sm text-[var(--danger)]">
            {error}
          </p>
        ) : null}
        <Button onClick={() => void save()} disabled={busy} className="min-h-11 self-start">
          {busy ? "Saving" : "Save"}
        </Button>
      </div>
    </Modal>
  );
}
