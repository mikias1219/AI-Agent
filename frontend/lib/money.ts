/** Money helpers shared by Today, Money and the agent cards. Amounts travel as integer minor units. */

export const DEFAULT_CURRENCY = "ETB";

/** 25000 → "250 ETB", 25050 → "250.50 ETB". */
export function formatMoney(minor: number, currency: string = DEFAULT_CURRENCY): string {
  const sign = minor < 0 ? "-" : "";
  const abs = Math.abs(minor);
  const major = Math.floor(abs / 100);
  const cents = abs % 100;
  const body = major.toLocaleString("en-US") + (cents ? `.${String(cents).padStart(2, "0")}` : "");
  return `${sign}${body} ${currency}`;
}

/** Parses a typed amount ("1,250.5") to major units; null when it is not a positive amount. */
export function parseAmount(text: string): number | null {
  const clean = text.replace(/[,\s]/g, "");
  if (!/^\d+(\.\d{1,2})?$/.test(clean)) return null;
  const value = Number(clean);
  return value > 0 ? value : null;
}

/** 3500000 → "35,000". Tiles show plain numbers; the currency is stated once on the page. */
export function formatAmount(minor: number): string {
  return formatMoney(minor, "").trim();
}

export type BudgetTone = "green" | "amber" | "red";

export function budgetTone(status: string): "success" | "warning" | "danger" {
  return status === "red" ? "danger" : status === "amber" ? "warning" : "success";
}

/** Current month as YYYY-MM in the browser's local time. */
export function currentPeriod(now: Date = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export function shiftPeriod(period: string, delta: number): string {
  const [y, m] = period.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return currentPeriod(d);
}

export function periodLabel(period: string): string {
  const [y, m] = period.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString(undefined, { month: "long", year: "numeric" });
}

/** Days remaining in the month, counting today. 0 for a past month, the full month for a future one. */
export function daysLeftInPeriod(period: string, now: Date = new Date()): number {
  const [y, m] = period.split("-").map(Number);
  const total = new Date(y, m, 0).getDate();
  const current = currentPeriod(now);
  if (period < current) return 0;
  if (period > current) return total;
  return total - now.getDate() + 1;
}
