"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { apiErrorMessage } from "@/lib/api/client";
import { updateTransaction, type FinCategory, type FinTransaction } from "@/lib/api/finance";
import { parseAmount } from "@/lib/money";

export type TxEditDrawerProps = {
  tx: FinTransaction | null;
  categories: readonly FinCategory[];
  onClose: () => void;
  onSaved: () => void;
  onDelete: (tx: FinTransaction) => void;
};

function localDate(iso: string): string {
  const d = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Edit one transaction in the side panel: amount, what, category, date, note. */
export function TxEditDrawer({ tx, categories, onClose, onSaved, onDelete }: TxEditDrawerProps) {
  const [amount, setAmount] = useState("");
  const [merchant, setMerchant] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [day, setDay] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!tx) return;
    setAmount(String(tx.amount_minor / 100));
    setMerchant(tx.merchant);
    setCategoryId(tx.category_id ?? "");
    setDay(localDate(tx.occurred_at));
    setNote(tx.note);
    setError("");
  }, [tx]);

  if (!tx) return null;
  const current = tx;
  const options = categories.filter((c) => c.kind === current.kind);
  const transfer = current.kind === "transfer";

  async function save(event: FormEvent) {
    event.preventDefault();
    const value = parseAmount(amount);
    if (value === null || value <= 0) {
      setError("Amount must be more than 0.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      // Send only what changed: a date-only value would reset the time of day.
      const patch: Record<string, unknown> = {};
      if (value * 100 !== current.amount_minor) patch.amount = amount.replace(/,/g, "").trim();
      if (merchant !== current.merchant) patch.merchant = merchant;
      if (note !== current.note) patch.note = note;
      if (day !== localDate(current.occurred_at)) patch.occurred_at = day;
      if ((categoryId || null) !== current.category_id) patch.category_id = categoryId || null;
      if (Object.keys(patch).length > 0) await updateTransaction(current.id, patch);
      window.dispatchEvent(new Event("compass:data-changed"));
      onSaved();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Drawer
      open
      onClose={onClose}
      title={current.kind === "income" ? "Edit income" : "Edit expense"}
    >
      {transfer ? (
        <p className="text-[length:var(--text-body)] text-[var(--muted)]">
          Transfers can't be edited. Delete it and add it again.
        </p>
      ) : (
        <form onSubmit={save} className="flex h-full flex-col gap-4">
          <Field label="Amount (ETB)" htmlFor="tx-amount">
            <Input
              id="tx-amount"
              inputMode="decimal"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          </Field>
          <Field label={current.kind === "income" ? "From" : "What"} htmlFor="tx-merchant">
            <Input
              id="tx-merchant"
              value={merchant}
              maxLength={120}
              onChange={(e) => setMerchant(e.target.value)}
            />
          </Field>
          <Field label="Category" htmlFor="tx-category-edit">
            <Select
              id="tx-category-edit"
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
            >
              <option value="">No category</option>
              {options.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Date" htmlFor="tx-date">
            <Input id="tx-date" type="date" value={day} onChange={(e) => setDay(e.target.value)} />
          </Field>
          <Field label="Note" htmlFor="tx-note">
            <Input
              id="tx-note"
              value={note}
              maxLength={500}
              onChange={(e) => setNote(e.target.value)}
            />
          </Field>
          {error ? (
            <p role="alert" className="text-[length:var(--text-body)] text-[var(--danger)]">
              {error}
            </p>
          ) : null}
          <div className="mt-auto flex items-center gap-2 border-t border-[var(--border)] pt-4">
            <Button type="button" variant="danger" onClick={() => onDelete(current)}>
              Delete
            </Button>
            <span className="flex-1" />
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              Save
            </Button>
          </div>
        </form>
      )}
    </Drawer>
  );
}
