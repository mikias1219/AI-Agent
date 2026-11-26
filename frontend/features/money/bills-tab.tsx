"use client";

import { FormEvent, useState } from "react";
import { CalendarClock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import { describeRule, type Recurrence } from "@/lib/api/habits";
import { createRecurring, listOccurrences, listRecurring } from "@/lib/api/finance";
import { formatMoney, parseAmount } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { OccurrenceList } from "./occurrence-list";

const FREQS: { id: Recurrence["freq"]; label: string }[] = [
  { id: "monthly", label: "Every month" },
  { id: "weekly", label: "Every week" },
  { id: "quarterly", label: "Every quarter" },
  { id: "yearly", label: "Every year" },
];

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function AddRule({ onAdded }: { onAdded: () => void }) {
  const { toast } = useToast();
  const [kind, setKind] = useState<"bill" | "income">("bill");
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [freq, setFreq] = useState<Recurrence["freq"]>("monthly");
  const [start, setStart] = useState(today());
  const [busy, setBusy] = useState(false);
  const value = parseAmount(amount);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!title.trim() || value === null) return;
    setBusy(true);
    try {
      await createRecurring({ kind, title: title.trim(), amount: value, rule: { freq, start } });
      setTitle("");
      setAmount("");
      onAdded();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 lg:items-end">
      <Field label="Type" htmlFor="rule-kind">
        <Select
          id="rule-kind"
          className="min-h-11"
          value={kind}
          onChange={(e) => setKind(e.target.value as "bill" | "income")}
        >
          <option value="bill">Bill</option>
          <option value="income">Income</option>
        </Select>
      </Field>
      <Field label="Name" htmlFor="rule-title">
        <Input
          id="rule-title"
          className="min-h-11"
          value={title}
          placeholder="Rent, Salary…"
          onChange={(e) => setTitle(e.target.value)}
        />
      </Field>
      <Field label="Amount" htmlFor="rule-amount">
        <Input
          id="rule-amount"
          inputMode="decimal"
          className="min-h-11"
          value={amount}
          placeholder="7500"
          onChange={(e) => setAmount(e.target.value)}
        />
      </Field>
      <Field label="Repeats" htmlFor="rule-freq">
        <Select
          id="rule-freq"
          className="min-h-11"
          value={freq}
          onChange={(e) => setFreq(e.target.value as Recurrence["freq"])}
        >
          {FREQS.map((f) => (
            <option key={f.id} value={f.id}>
              {f.label}
            </option>
          ))}
        </Select>
      </Field>
      <Field label="First date" htmlFor="rule-start">
        <Input
          id="rule-start"
          type="date"
          className="min-h-11"
          value={start}
          onChange={(e) => setStart(e.target.value)}
        />
      </Field>
      <div className="sm:col-span-2 lg:col-span-5">
        <Button
          type="submit"
          className="min-h-11"
          loading={busy}
          disabled={!title.trim() || value === null}
        >
          Add {kind === "income" ? "income" : "bill"}
        </Button>
      </div>
    </form>
  );
}

export function BillsTab() {
  const upcoming = useLoad(() => {
    const to = new Date(Date.now() + 45 * 86_400_000);
    return listOccurrences(
      undefined,
      `${to.getFullYear()}-${String(to.getMonth() + 1).padStart(2, "0")}-${String(to.getDate()).padStart(2, "0")}`,
    );
  });
  const rules = useLoad(listRecurring);
  const reload = () => {
    void upcoming.reload();
    void rules.reload();
  };

  if (upcoming.error) return <ErrorBlock what="bills" message={upcoming.error} onRetry={reload} />;
  if (!upcoming.data) return <CardSkeleton rows={4} />;
  const open = upcoming.data.filter((o) => ["expected", "overdue", "partial"].includes(o.status));

  return (
    <Card
      id="bills-upcoming"
      title="Income and bills"
      description="Mark each one when the money moves. Next 45 days."
    >
      {open.length === 0 ? (
        <EmptyState
          compact
          icon={CalendarClock}
          title="Nothing due in the next 45 days"
          description="Add rent, salary or any repeating bill below."
        />
      ) : (
        <OccurrenceList items={open} onChange={reload} />
      )}
      <details className="mt-4 border-t border-[var(--border)] pt-3">
        <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium text-[var(--accent)]">
          Manage repeating bills and income
          {rules.data && rules.data.length > 0 ? ` (${rules.data.length})` : ""}
        </summary>
        <div className="mt-3 flex flex-col gap-5">
          {rules.data && rules.data.length > 0 ? (
            <ul className="flex flex-col divide-y divide-[var(--border)]">
              {rules.data.map((r) => (
                <li
                  key={r.id}
                  className="grid grid-cols-[minmax(0,1fr)_auto_6rem] items-center gap-x-3 py-2.5 text-sm first:pt-0 last:pb-0"
                >
                  <span className="truncate text-[var(--ink)]">{r.title}</span>
                  <span className="text-xs text-[var(--muted)]">{describeRule(r.rule)}</span>
                  <span className="text-right font-medium tabular-nums">
                    {formatMoney(r.amount_minor)}
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
          <AddRule onAdded={reload} />
        </div>
      </details>
    </Card>
  );
}
