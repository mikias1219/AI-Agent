"use client";

import { FormEvent, useState } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  createTransaction,
  getCategories,
  parseQuickText,
  quickExpense,
  type ParsedDraft,
} from "@/lib/api/finance";
import { formatMoney, parseAmount } from "@/lib/money";
import { useLoad } from "@/lib/use-load";

const CHIPS = 6;

/**
 * The one way to add money: type "250" and tap a category, or type "lunch 250 cash at Kaldi's"
 * to get a preview first. Used on Today and on the Money overview.
 */
export function QuickAdd({ onSaved }: { onSaved: () => void }) {
  const { toast } = useToast();
  const categories = useLoad(getCategories);
  const [text, setText] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [draft, setDraft] = useState<ParsedDraft["draft"] | null>(null);
  const [busy, setBusy] = useState(false);

  const expense = (categories.data ?? []).filter((c) => c.kind === "expense");
  const amount = parseAmount(text);
  const nameOf = (id: string | null) =>
    categories.data?.find((c) => c.id === id)?.name ?? "No category";

  function reset() {
    setText("");
    setCategory(null);
    setDraft(null);
    onSaved();
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      if (draft) {
        await createTransaction({
          kind: draft.kind,
          amount: draft.amount_minor / 100,
          merchant: draft.merchant,
          note: draft.note,
          account_id: draft.account_id ?? undefined,
          category_id: category ?? draft.category_id ?? undefined,
        });
        toast("Saved");
        reset();
      } else if (amount !== null) {
        await quickExpense(amount, category);
        toast(`Saved ${formatMoney(Math.round(amount * 100))}`);
        reset();
      } else {
        const parsed = await parseQuickText(text);
        setDraft(parsed.draft);
        setCategory(parsed.draft.category_id);
      }
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3" aria-label="Add money">
      <div className="flex gap-2">
        <label htmlFor="quick-money" className="sr-only">
          Amount or a note like lunch 250 cash
        </label>
        <Input
          id="quick-money"
          value={text}
          inputMode="text"
          autoComplete="off"
          placeholder="250  or  lunch 250 cash at Kaldi's"
          className="min-h-11 flex-1"
          onChange={(e) => {
            setText(e.target.value);
            setDraft(null);
          }}
        />
        <Button type="submit" className="min-h-11" loading={busy} disabled={!text.trim()}>
          <Plus className="h-4 w-4" aria-hidden />
          {draft || amount !== null ? "Save" : "Preview"}
        </Button>
      </div>
      {draft ? (
        <p
          role="status"
          className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-2 text-sm text-[var(--ink)]"
        >
          {draft.kind === "income" ? "Income" : "Expense"} {formatMoney(draft.amount_minor)} ·{" "}
          {nameOf(category ?? draft.category_id)}
          {draft.merchant ? ` · ${draft.merchant}` : ""}. Not saved yet.
        </p>
      ) : null}
      {expense.length > 0 && draft?.kind !== "income" ? (
        <div className="flex flex-wrap gap-2" role="group" aria-label="Category">
          {expense.slice(0, CHIPS).map((c) => (
            <button
              key={c.id}
              type="button"
              aria-pressed={category === c.id}
              onClick={() => setCategory(category === c.id ? null : c.id)}
              className={`min-h-11 rounded-full border px-3 text-xs sm:min-h-0 sm:py-1 ${
                category === c.id
                  ? "border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent-strong)]"
                  : "border-[var(--border)] bg-[var(--canvas)] text-[var(--muted)] hover:text-[var(--ink)]"
              }`}
            >
              {c.name}
            </button>
          ))}
        </div>
      ) : null}
    </form>
  );
}
