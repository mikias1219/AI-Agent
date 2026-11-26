"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  DEDUCTIONS,
  INCOME_COMPONENTS,
  listPayslips,
  savePayslip,
  type Payslip,
} from "@/lib/api/finance";
import { formatMoney, parseAmount } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

function pick(values: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim() !== ""));
}

function PayslipForm({ onSaved }: { onSaved: () => void }) {
  const { toast } = useToast();
  const [payday, setPayday] = useState(() => new Date().toISOString().slice(0, 10));
  const [components, setComponents] = useState<Record<string, string>>({});
  const [deductions, setDeductions] = useState<Record<string, string>>({});
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const sum = (values: Record<string, string>) =>
    Object.values(values).reduce((total, v) => total + (parseAmount(v) ?? 0), 0);
  const gross = sum(components);
  const net = gross - sum(deductions);

  async function submit() {
    setError("");
    const all = { ...components, ...deductions };
    const bad = Object.entries(all).find(([, v]) => v.trim() !== "" && parseAmount(v) === null);
    if (bad) return setError("Amounts must be positive numbers such as 1,500 or 1500.50.");
    if (gross <= 0) return setError("Enter at least your basic salary.");
    setBusy(true);
    try {
      await savePayslip({
        payday,
        components: pick(components),
        deductions: pick(deductions),
        record_income: true,
      });
      toast("Payslip saved. Net pay added to income.", "success");
      setComponents({});
      setDeductions({});
      onSaved();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const fields = (
    list: readonly { id: string; label: string }[],
    values: Record<string, string>,
    set: (next: Record<string, string>) => void,
  ) =>
    list.map((f) => (
      <Field key={f.id} label={f.label} htmlFor={`slip-${f.id}`}>
        <Input
          id={`slip-${f.id}`}
          inputMode="decimal"
          value={values[f.id] ?? ""}
          onChange={(e) => set({ ...values, [f.id]: e.target.value })}
          placeholder="0"
        />
      </Field>
    ));

  return (
    <Card
      id="payslip-form"
      title="Add a payslip"
      description="Gross minus deductions is the net that lands in your account."
    >
      <div className="flex flex-col gap-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Payday" htmlFor="slip-payday">
            <Input
              id="slip-payday"
              type="date"
              value={payday}
              onChange={(e) => setPayday(e.target.value)}
            />
          </Field>
          {fields(INCOME_COMPONENTS.slice(0, 1), components, setComponents)}
        </div>
        <button
          type="button"
          onClick={() => setMore(!more)}
          aria-expanded={more}
          className="min-h-11 self-start text-sm font-medium text-[var(--accent)] hover:underline"
        >
          {more ? "Fewer options" : "More options: allowances and deductions"}
        </button>
        {more ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {fields(INCOME_COMPONENTS.slice(1), components, setComponents)}
            {fields(DEDUCTIONS, deductions, setDeductions)}
          </div>
        ) : null}
        <p className="text-sm text-[var(--ink)] tabular-nums">
          Gross {formatMoney(gross * 100)} · Net{" "}
          <span
            className={net < 0 ? "text-[var(--danger)]" : "font-semibold text-[var(--success)]"}
          >
            {formatMoney(net * 100)}
          </span>
        </p>
        {error ? (
          <p role="alert" className="text-sm text-[var(--danger)]">
            {error}
          </p>
        ) : null}
        <Button onClick={() => void submit()} disabled={busy} className="min-h-11 self-start">
          {busy ? "Saving" : "Save payslip"}
        </Button>
      </div>
    </Card>
  );
}

function PayslipRow({ slip }: { slip: Payslip }) {
  const change = slip.net_change_pct;
  return (
    <li className="flex flex-wrap items-center justify-between gap-2 py-3 text-sm">
      <div className="min-w-0">
        <p className="font-medium text-[var(--ink)]">
          {slip.period_start} to {slip.period_end}
        </p>
        <p className="text-xs text-[var(--muted)] tabular-nums">
          Gross {formatMoney(slip.gross_minor)}
          {Object.entries(slip.shares)
            .filter(([k]) => !k.startsWith("deduction:"))
            .map(([k, v]) => ` · ${k} ${v}%`)
            .join("")}
        </p>
      </div>
      <div className="text-right tabular-nums">
        <p className="font-semibold text-[var(--ink)]">{formatMoney(slip.net_minor)}</p>
        {change !== null && change !== undefined ? (
          <p
            className={`text-xs ${change >= 0 ? "text-[var(--success)]" : "text-[var(--danger)]"}`}
          >
            {change > 0 ? "+" : ""}
            {change}% since last period
          </p>
        ) : null}
      </div>
    </li>
  );
}

export function IncomeTab() {
  const { data, error, loading, reload } = useLoad(listPayslips);
  return (
    <div className="flex flex-col gap-4">
      <PayslipForm onSaved={() => void reload()} />
      {loading && !data ? (
        <CardSkeleton rows={3} />
      ) : error ? (
        <ErrorBlock what="payslips" message={error} onRetry={() => void reload()} />
      ) : data && data.items.length > 0 ? (
        <Card id="payslip-history" title="Pay history">
          <ul className="divide-y divide-[var(--border)]">
            {data.items.map((s) => (
              <PayslipRow key={s.id} slip={s} />
            ))}
          </ul>
        </Card>
      ) : (
        <EmptyState compact title="No payslips yet" description="Add your first one above." />
      )}
    </div>
  );
}
