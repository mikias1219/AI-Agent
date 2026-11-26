"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  DEDUCTIONS,
  deletePayslip,
  getAccounts,
  INCOME_COMPONENTS,
  listPayslips,
  previewPayslip,
  savePayslip,
  type Payslip,
  type PayslipPreview,
} from "@/lib/api/finance";
import { formatMoney, parseAmount } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";

function pick(values: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(values).filter(([, v]) => v.trim() !== ""));
}

const PREVIEW_DELAY_MS = 300;

function dateLabel(iso: string): string {
  return new Date(`${iso}T12:00:00`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/** "35% − 2,050" for the bracket the taxable pay falls in, so the number explains itself. */
function taxRule(preview: PayslipPreview): string | null {
  const gross = preview.gross_minor / 100;
  const bracket = preview.rules.tax_brackets.find((b) => b.up_to === null || gross <= b.up_to);
  if (!bracket || bracket.rate_pct === 0) return bracket ? "below the tax-free limit" : null;
  return `${bracket.rate_pct}% − ${bracket.deduction.toLocaleString("en-US")}`;
}

/**
 * Payslip form. Basic salary is enough: income tax and pension are calculated by the backend
 * from the payroll rules while you type; typing either one overrides the calculation.
 */
function PayslipForm({ onSaved }: { onSaved: () => void }) {
  const { toast } = useToast();
  const [payday, setPayday] = useState(() => new Date().toISOString().slice(0, 10));
  const [components, setComponents] = useState<Record<string, string>>({});
  const [deductions, setDeductions] = useState<Record<string, string>>({});
  const [accountId, setAccountId] = useState("");
  const [more, setMore] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<PayslipPreview | null>(null);
  const accounts = useLoad(getAccounts);

  const invalid = Object.entries({ ...components, ...deductions }).find(
    ([, v]) => v.trim() !== "" && parseAmount(v) === null,
  );
  const hasIncome = Object.values(components).some((v) => (parseAmount(v) ?? 0) > 0);

  useEffect(() => {
    if (invalid || !hasIncome || !payday) {
      setPreview(null);
      return;
    }
    let cancelled = false;
    const id = window.setTimeout(() => {
      previewPayslip({ payday, components: pick(components), deductions: pick(deductions) })
        .then((next) => {
          if (!cancelled) {
            setPreview(next);
            setError("");
          }
        })
        .catch((err) => {
          if (!cancelled) {
            setPreview(null);
            setError(apiErrorMessage(err));
          }
        });
    }, PREVIEW_DELAY_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(id);
    };
  }, [payday, components, deductions, invalid, hasIncome]);

  async function submit() {
    setError("");
    if (invalid) return setError("Amounts must be positive numbers such as 1,500 or 1500.50.");
    if (!hasIncome) return setError("Enter at least your basic salary.");
    setBusy(true);
    try {
      await savePayslip({
        payday,
        components: pick(components),
        deductions: pick(deductions),
        account_id: accountId || null,
        record_income: true,
      });
      toast("Payslip saved. Net pay added to income.", "success");
      setComponents({});
      setDeductions({});
      setPreview(null);
      window.dispatchEvent(new Event("compass:data-changed"));
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
    placeholder = "0",
  ) =>
    list.map((f) => (
      <Field key={f.id} label={f.label} htmlFor={`slip-${f.id}`}>
        <Input
          id={`slip-${f.id}`}
          inputMode="decimal"
          value={values[f.id] ?? ""}
          onChange={(e) => set({ ...values, [f.id]: e.target.value })}
          placeholder={placeholder}
        />
      </Field>
    ));

  const auto = new Set(preview?.auto ?? []);
  const line = (label: string, minor: number, note?: string | null, strong = false) => (
    <div className="flex items-baseline justify-between gap-3 py-1">
      <dt className={strong ? "font-semibold text-[var(--ink)]" : "text-[var(--ink)]"}>
        {label}
        {note ? <span className="ml-1.5 text-[var(--muted)]">({note})</span> : null}
      </dt>
      <dd
        className={`tabular-nums ${strong ? "text-base font-semibold text-[var(--success)]" : minor < 0 ? "text-[var(--danger)]" : "text-[var(--ink)]"}`}
      >
        {minor < 0 ? "−" : ""}
        {formatMoney(Math.abs(minor))}
      </dd>
    </div>
  );

  return (
    <Card
      id="payslip-form"
      title="Add a payslip"
      description="Enter your basic salary. Income tax and pension are calculated for you."
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {fields(INCOME_COMPONENTS.slice(0, 1), components, setComponents)}
            <Field label="Payday" htmlFor="slip-payday">
              <Input
                id="slip-payday"
                type="date"
                value={payday}
                onChange={(e) => setPayday(e.target.value)}
              />
            </Field>
            <Field label="Paid into" htmlFor="slip-account">
              <Select
                id="slip-account"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
              >
                <option value="">Default account</option>
                {(accounts.data ?? []).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>
          <button
            type="button"
            onClick={() => setMore(!more)}
            aria-expanded={more}
            className="min-h-11 self-start text-sm font-medium text-[var(--accent)] hover:underline"
          >
            {more ? "Fewer options" : "More: allowances, loan, or override tax and pension"}
          </button>
          {more ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {fields(INCOME_COMPONENTS.slice(1), components, setComponents)}
              {fields(DEDUCTIONS.slice(0, 2), deductions, setDeductions, "Calculated")}
              {fields(DEDUCTIONS.slice(2), deductions, setDeductions)}
            </div>
          ) : null}
        </div>

        <div
          aria-live="polite"
          className="flex flex-col gap-2 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--subtle)] p-4 text-sm"
        >
          <p className="text-xs font-semibold tracking-[0.06em] text-[var(--muted)] uppercase">
            Your pay
          </p>
          {preview ? (
            <>
              <dl className="flex flex-col">
                {line("Gross", preview.gross_minor)}
                {line(
                  "Income tax",
                  -(preview.deductions.income_tax ?? 0),
                  auto.has("income_tax") ? taxRule(preview) : "typed",
                )}
                {line(
                  "Pension",
                  -(preview.deductions.pension ?? 0),
                  auto.has("pension") ? `${preview.rules.pension_employee_pct}% of basic` : "typed",
                )}
                {preview.deductions.loan ? line("Loan", -preview.deductions.loan) : null}
                {preview.deductions.other ? line("Other", -preview.deductions.other) : null}
              </dl>
              <div className="border-t border-[var(--border)] pt-2">
                {line("Net pay", preview.net_minor, null, true)}
              </div>
              <p className="text-xs text-[var(--muted)]">
                Pay period {dateLabel(preview.period_start)} to {dateLabel(preview.period_end)}
              </p>
            </>
          ) : (
            <p className="text-[var(--muted)]">
              Type your basic salary to see tax, pension and net pay.
            </p>
          )}
        </div>
      </div>
      {error ? (
        <p role="alert" className="mt-3 text-sm text-[var(--danger)]">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-end border-t border-[var(--border)] pt-4">
        <Button onClick={() => void submit()} loading={busy} disabled={!hasIncome}>
          Save payslip
        </Button>
      </div>
    </Card>
  );
}

function PayslipRow({ slip, onDeleted }: { slip: Payslip; onDeleted: () => void }) {
  const { toast } = useToast();
  async function remove() {
    if (!window.confirm("Delete this payslip and the net pay it added to income?")) return;
    try {
      await deletePayslip(slip.id);
      toast("Payslip deleted.");
      window.dispatchEvent(new Event("compass:data-changed"));
      onDeleted();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }
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
        <button
          type="button"
          onClick={() => void remove()}
          className="mt-1 min-h-8 text-xs font-medium text-[var(--danger)] hover:underline"
        >
          Delete
        </button>
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
              <PayslipRow key={s.id} slip={s} onDeleted={() => void reload()} />
            ))}
          </ul>
        </Card>
      ) : (
        <EmptyState compact title="No payslips yet" description="Add your first one above." />
      )}
    </div>
  );
}
