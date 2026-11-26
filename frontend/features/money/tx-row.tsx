"use client";

import type { ReactNode } from "react";
import type { FinTransaction } from "@/lib/api/finance";
import { formatMoney } from "@/lib/money";

/** One transaction line, used by Overview (recent) and Activity (full list) so they match. */
export function TxRow({
  tx,
  categoryName,
  action,
}: {
  tx: FinTransaction;
  categoryName?: string;
  action?: ReactNode;
}) {
  const title = tx.merchant || categoryName || (tx.kind === "transfer" ? "Transfer" : "Untitled");
  const sign = tx.kind === "income" ? "+" : tx.kind === "expense" ? "-" : "";
  return (
    <li className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-x-3 py-3 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-[var(--ink)]">{title}</p>
        <p className="truncate text-xs text-[var(--muted)]">
          {new Date(tx.occurred_at).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}
          {categoryName && tx.merchant ? ` · ${categoryName}` : ""}
          {tx.note ? ` · ${tx.note}` : ""}
          {tx.created_by === "agent" ? " · by Compass" : ""}
        </p>
      </div>
      <span
        className={`text-right text-sm font-medium tabular-nums ${tx.kind === "income" ? "text-[var(--success)]" : "text-[var(--ink)]"}`}
      >
        {sign}
        {formatMoney(tx.amount_minor, tx.currency)}
      </span>
      <span className="flex min-w-10 justify-end gap-0.5">{action}</span>
    </li>
  );
}
