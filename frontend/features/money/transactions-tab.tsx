"use client";

import { useState } from "react";
import { Pencil, Plus, Receipt, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { openQuickAdd } from "@/components/shell/quick-add-sheet";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { IconButton } from "@/components/ui/icon-button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { StatusChip } from "@/components/ui/status-chip";
import { useToast } from "@/components/ui/toast";
import { apiErrorMessage } from "@/lib/api/client";
import {
  deleteTransaction,
  getCategories,
  listTransactions,
  type FinTransaction,
} from "@/lib/api/finance";
import { formatMoney } from "@/lib/money";
import { useLoad } from "@/lib/use-load";
import { CardSkeleton, ErrorBlock } from "@/features/learn/states";
import { TxEditDrawer } from "./tx-edit-drawer";
import { TxRow } from "./tx-row";

export function TransactionsTab({ period }: { period: string }) {
  const { toast } = useToast();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [editing, setEditing] = useState<FinTransaction | null>(null);
  const categories = useLoad(getCategories);
  const rows = useLoad(
    () =>
      listTransactions({ period, q: q.trim() || undefined, category_id: category || undefined }),
    [period, q, category],
  );
  const names = new Map((categories.data ?? []).map((c) => [c.id, c.name]));

  async function remove(id: string) {
    try {
      await deleteTransaction(id);
      setEditing(null);
      toast("Deleted. You can restore it for 30 days.");
      void rows.reload();
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  return (
    <Card
      id="money-transactions"
      title="Activity"
      action={
        <Button size="sm" variant="secondary" onClick={() => openQuickAdd("expense")}>
          <Plus className="h-4 w-4" aria-hidden />
          New
        </Button>
      }
    >
      <div className="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem]">
        <label className="sr-only" htmlFor="tx-search">
          Search merchant or note
        </label>
        <Input
          id="tx-search"
          className="min-h-11"
          placeholder="Search merchant or note"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <label className="sr-only" htmlFor="tx-category">
          Category
        </label>
        <Select
          id="tx-category"
          className="min-h-11"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        >
          <option value="">All categories</option>
          {(categories.data ?? []).map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </Select>
      </div>
      {rows.error ? (
        <ErrorBlock what="transactions" message={rows.error} onRetry={() => void rows.reload()} />
      ) : !rows.data ? (
        <CardSkeleton rows={4} />
      ) : rows.data.length === 0 ? (
        <EmptyState
          compact
          icon={Receipt}
          title="No transactions"
          description="Add your first expense or income, or type it to the Money agent above."
          action={
            <div className="flex gap-2">
              <Button size="sm" onClick={() => openQuickAdd("expense")}>
                Add expense
              </Button>
              <Button size="sm" variant="secondary" onClick={() => openQuickAdd("income")}>
                Add income
              </Button>
            </div>
          }
        />
      ) : (
        <ul className="flex flex-col divide-y divide-[var(--border)]">
          {rows.data.map((tx) => (
            <TxRow
              key={tx.id}
              tx={tx}
              categoryName={names.get(tx.category_id ?? "")}
              action={
                <>
                  <IconButton
                    label={`Edit transaction ${tx.merchant || ""}`.trim()}
                    onClick={() => setEditing(tx)}
                  >
                    <Pencil className="h-4 w-4" aria-hidden />
                  </IconButton>
                  <IconButton
                    label={`Delete transaction ${tx.merchant || ""}`.trim()}
                    onClick={() => void remove(tx.id)}
                  >
                    <Trash2 className="h-4 w-4" aria-hidden />
                  </IconButton>
                </>
              }
            />
          ))}
        </ul>
      )}
      <TxEditDrawer
        tx={editing}
        categories={categories.data ?? []}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null);
          toast("Saved.", "success");
          void rows.reload();
        }}
        onDelete={(tx) => void remove(tx.id)}
      />
    </Card>
  );
}
