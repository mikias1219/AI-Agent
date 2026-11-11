"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api/client";
import { createMemory } from "@/lib/api/memories";
import type { MemoryProposal, UsedMemory } from "@/lib/api/types";

export function SaveMemoryChip({
  proposal,
  onSaved,
}: {
  proposal: MemoryProposal;
  onSaved?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (dismissed) return null;

  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      await createMemory({
        kind: proposal.kind,
        content: proposal.content,
        source_run_id: proposal.source_run_id ?? undefined,
      });
      setSaved(true);
      onSaved?.();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm">
      {saved ? (
        <p className="text-[var(--muted)]">
          Saved to memory.{" "}
          <Link href="/memory" className="text-[var(--accent)] underline-offset-2 hover:underline">
            View
          </Link>
        </p>
      ) : (
        <>
          <p className="text-[var(--ink)]">
            Save to memory? <span className="text-[var(--muted)]">({proposal.kind})</span>
          </p>
          <p className="mt-1 text-[var(--muted)]">{proposal.content}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            <Button size="sm" disabled={busy} onClick={() => void confirm()}>
              {busy ? "Saving…" : "Save"}
            </Button>
            <Button size="sm" variant="secondary" disabled={busy} onClick={() => setDismissed(true)}>
              Dismiss
            </Button>
          </div>
          {error ? (
            <p className="mt-2 text-xs text-[var(--danger)]" role="alert">
              {error}
            </p>
          ) : null}
        </>
      )}
    </div>
  );
}

export function UsedMemoryChips({ items }: { items: UsedMemory[] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {items.map((item) => (
        <Link
          key={item.id}
          href={`/memory?highlight=${encodeURIComponent(item.id)}`}
          className="inline-flex max-w-full items-center rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] px-3 py-1 text-xs text-[var(--ink)] hover:border-[var(--accent)]"
          title={item.content}
        >
          Used memory · {item.content.slice(0, 48)}
          {item.content.length > 48 ? "…" : ""}
        </Link>
      ))}
    </div>
  );
}
