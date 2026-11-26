import { api } from "./client";
import type { Recurrence } from "./habits";

export type FinAccount = {
  id: string;
  name: string;
  type: string;
  currency: string;
  balance_minor: number;
};
export type FinCategory = {
  id: string;
  name: string;
  kind: "income" | "expense";
  is_fixed: boolean;
};

export type FinTransaction = {
  id: string;
  kind: "income" | "expense" | "transfer";
  amount_minor: number;
  currency: string;
  occurred_at: string;
  account_id: string | null;
  category_id: string | null;
  status: string;
  merchant: string;
  note: string;
  occurrence_id: string | null;
  created_by: "user" | "agent";
};

export type BudgetLine = {
  category_id: string;
  category: string;
  planned_minor: number;
  actual_minor: number;
  remaining_minor: number;
  overspend_minor: number;
  utilisation_pct: number;
  status: "green" | "amber" | "red";
  alert_at_pct: number;
};

export type Budget = {
  id: string;
  name: string;
  type: string;
  period_start: string;
  period_end: string;
  income_plan_minor: number;
  planned_minor: number;
  unallocated_minor: number;
  actual_minor: number;
  lines: BudgetLine[];
};

export type Occurrence = {
  id: string;
  rule_id: string;
  title: string;
  kind: "income" | "bill";
  due_date: string;
  expected_minor: number;
  paid_minor: number;
  remaining_minor: number;
  status: "expected" | "paid" | "partial" | "overdue" | "skipped";
};

export type RecurringRule = {
  id: string;
  version: number;
  kind: "income" | "bill";
  title: string;
  amount_minor: number;
  rule: Recurrence;
  category_id: string | null;
  account_id: string | null;
};

export type FinanceSummary = {
  period: string;
  income_minor: number;
  spent_minor: number;
  saved_minor: number;
  budget_planned_minor: number;
  left_in_budget_minor: number | null;
  savings_rate_pct: number;
  balance_minor: number;
  expected_end_balance_minor: number;
  budget: Budget | null;
  upcoming: Occurrence[];
  currency: string;
};

export type MoneyRow = {
  spent_today_minor: number;
  left_this_month_minor: number | null;
  next_bill: Occurrence | null;
  currency: string;
};

export type SavingsGoal = {
  id: string;
  name: string;
  target_minor: number;
  saved_minor: number;
  progress_pct: number;
  target_date: string | null;
  monthly_contribution_minor: number;
  projected_completion: string | null;
  on_track: boolean | null;
};

export type ParsedDraft = {
  draft: {
    kind: "income" | "expense";
    amount_minor: number;
    merchant: string;
    category_id: string | null;
    account_id: string | null;
    note: string;
  };
  saved: false;
};

export type MonthlyReportRow = {
  period: string;
  income_minor: number;
  spent_minor: number;
  saved_minor: number;
};

const json = (body: unknown) => ({ method: "POST", body: JSON.stringify(body) });

export const getMoneyRow = () => api<MoneyRow>("/finance/today-row");
export const getAccounts = () => api<FinAccount[]>("/finance/accounts");
export const getCategories = () => api<FinCategory[]>("/finance/categories");
export const getSummary = (period?: string) =>
  api<FinanceSummary>(`/finance/summary${period ? `?period=${period}` : ""}`);
export const listTransactions = (params: { period?: string; q?: string; category_id?: string }) => {
  const query = new URLSearchParams();
  if (params.period) query.set("period", params.period);
  if (params.q) query.set("q", params.q);
  if (params.category_id) query.set("category_id", params.category_id);
  return api<FinTransaction[]>(`/finance/transactions?${query}`);
};
export const quickExpense = (amount: number | string, category_id?: string | null) =>
  api<FinTransaction>("/finance/transactions/quick", json({ amount, category_id }));
export const createTransaction = (body: Record<string, unknown>) =>
  api<FinTransaction[]>("/finance/transactions", json(body));
export const deleteTransaction = (id: string) =>
  api<unknown>(`/finance/transactions/${id}`, { method: "DELETE" }).catch(() => undefined);
export const parseQuickText = (text: string) => api<ParsedDraft>("/finance/parse", json({ text }));

export const listBudgets = () => api<Budget[]>("/finance/budgets");
export const createBudget = (body: Record<string, unknown>) =>
  api<Budget>("/finance/budgets", json(body));
export const copyBudget = (id: string, period: string) =>
  api<Budget>(`/finance/budgets/${id}/copy`, json({ period }));
export const putBudgetLines = (id: string, lines: { category_id: string; planned: number }[]) =>
  api<Budget>(`/finance/budgets/${id}/lines`, { method: "PUT", body: JSON.stringify(lines) });

export const listRecurring = () => api<RecurringRule[]>("/finance/recurring");
export const createRecurring = (body: Record<string, unknown>) =>
  api<RecurringRule>("/finance/recurring", json(body));
export const listOccurrences = (from?: string, to?: string) => {
  const query = new URLSearchParams();
  if (from) query.set("from", from);
  if (to) query.set("to", to);
  return api<Occurrence[]>(`/finance/occurrences?${query}`);
};
export const settleOccurrence = (id: string, body: { status?: string; amount?: number }) =>
  api<unknown>(`/finance/occurrences/${id}/settle`, json(body));

export const listSavingsGoals = () => api<SavingsGoal[]>("/finance/savings-goals");
export const createSavingsGoal = (body: Record<string, unknown>) =>
  api<{ id: string }>("/finance/savings-goals", json(body));
export const contributeToGoal = (id: string, amount: number) =>
  api<unknown>(`/finance/savings-goals/${id}/contributions`, json({ amount }));

export const monthlyReport = (months = 6) =>
  api<{ rows: MonthlyReportRow[] }>(`/finance/reports/monthly?months=${months}`);

export type CategorySpend = { category_id: string; category: string; amount_minor: number };
export const categoryReport = (period: string) =>
  api<{ period: string; rows: CategorySpend[] }>(`/finance/reports/category?period=${period}`);

// -- Money by period, payslips (Improvement Plan) ------------------------------------------

export const RANGES = [
  { id: "today", label: "Today" },
  { id: "week", label: "Week" },
  { id: "month", label: "Month" },
  { id: "last_month", label: "Last month" },
  { id: "next_month", label: "Next month" },
  { id: "year", label: "Year" },
  { id: "custom", label: "Custom" },
] as const;
export type RangeId = (typeof RANGES)[number]["id"];

export type ShareRow = { amount_minor: number; share_pct: number };
export type OverviewCategory = ShareRow & {
  category: string;
  previous_minor: number;
  change_pct: number | null;
};
export type Forecast = {
  expected_income_minor: number;
  committed_minor: number;
  variable_minor: number;
  planned_savings_minor: number;
  left_minor: number;
  buffer_minor: number;
  below_buffer: boolean;
  trim_suggestions: { category: string; amount_minor: number }[];
  basis: string;
  has_payslip: boolean;
};
export type MoneyOverview = {
  range: RangeId;
  first: string;
  last: string;
  previous: { first: string; last: string };
  currency: string;
  income_minor: number;
  spent_minor: number;
  saved_minor: number;
  net_minor: number;
  left_minor: number;
  income_change_pct: number | null;
  spent_change_pct: number | null;
  saved_change_pct: number | null;
  net_change_pct: number | null;
  budget_planned_minor: number;
  pace: number | null;
  daily_allowance_minor: number | null;
  days_left: number;
  savings_rate_pct: number;
  income_breakdown: (ShareRow & { source: string })[];
  categories: OverviewCategory[];
  top_categories: OverviewCategory[];
  biggest_spends: { id: string; merchant: string; category: string; amount_minor: number }[];
  by_day: { day: string; spent_minor: number }[];
  transaction_count: number;
  forecast: Forecast | null;
};

export const getOverview = (range: RangeId, custom?: { start: string; end: string }) => {
  const q = new URLSearchParams({ range });
  if (range === "custom" && custom) {
    q.set("start", custom.start);
    q.set("end", custom.end);
  }
  return api<MoneyOverview>(`/finance/overview?${q}`);
};

export const INCOME_COMPONENTS = [
  { id: "basic", label: "Basic salary" },
  { id: "allowance", label: "Allowances" },
  { id: "benefit", label: "Benefits" },
  { id: "incentive", label: "Incentive" },
  { id: "performance", label: "Performance pay" },
] as const;
export const DEDUCTIONS = [
  { id: "income_tax", label: "Income tax" },
  { id: "pension", label: "Pension" },
  { id: "loan", label: "Loan" },
  { id: "other", label: "Other" },
] as const;

export type Payslip = {
  id: string;
  period_start: string;
  period_end: string;
  payday: string;
  components: Record<string, number>;
  deductions: Record<string, number>;
  gross_minor: number;
  net_minor: number;
  shares: Record<string, number>;
  net_change_pct?: number | null;
};
export const listPayslips = () => api<{ items: Payslip[] }>("/finance/payslips");
export const savePayslip = (body: {
  payday: string;
  components: Record<string, string>;
  deductions: Record<string, string>;
  account_id?: string | null;
  record_income: boolean;
}) => api<Payslip>("/finance/payslips", json(body));

// -- Money agent insight sources and payroll (redesign) -----------------------------------

export type BudgetAlert = {
  category: string;
  status: "amber" | "red" | string;
  utilisation_pct: number;
  remaining_minor: number;
  days_left: number;
};
export type MoneyInsightItem = { kind: string; severity: string; message: string };

export const getMoneyAlerts = () =>
  api<{ budget: BudgetAlert[]; due: Occurrence[] }>("/finance/alerts");
export const getMoneyInsights = () => api<{ items: MoneyInsightItem[] }>("/finance/insights");

export type PayslipPreview = Payslip & {
  /** Deductions that were calculated rather than typed in. */
  auto: string[];
  rules: PayrollRules;
};
export type PayrollRules = {
  tax_brackets: { up_to: number | null; rate_pct: number; deduction: number }[];
  pension_employee_pct: number;
  pension_employer_pct: number;
  period_start_day: number;
};
export type PayslipInput = {
  payday: string;
  components: Record<string, string>;
  deductions: Record<string, string>;
  account_id?: string | null;
  record_income?: boolean;
  period_start_day?: number;
};
export const previewPayslip = (body: PayslipInput) =>
  api<PayslipPreview>("/finance/payslips/preview", json(body));
export const getPayrollRules = () => api<PayrollRules>("/finance/payroll-rules");

export const updateAccount = (
  id: string,
  body: { name?: string; type?: string; archived?: boolean },
) =>
  api<FinAccount>(`/finance/accounts/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
export const updateTransaction = (id: string, body: Record<string, unknown>) =>
  api<FinTransaction>(`/finance/transactions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
