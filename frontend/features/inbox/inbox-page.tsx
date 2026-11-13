"use client";

import { useCallback, useEffect, useState } from "react";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Tabs } from "@/components/ui/tabs";
import { apiErrorMessage } from "@/lib/api/client";
import {
  acceptSuggestion,
  dismissSuggestion,
  getInbox,
  type InboxItem,
  type InboxSuggestionItem,
  type InboxTab,
} from "@/lib/api/inbox";
import { expiresIn, itemKey, outcomeMessage, statusLabel } from "./inbox-logic";

export function InboxPage() {
  const [tab, setTab] = useState<InboxTab>("open");
  const [items, setItems] = useState<InboxItem[]>([]);
  const [openCount, setOpenCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (which: InboxTab) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getInbox(which);
      setItems(payload.items);
      setOpenCount(payload.counts.open);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(tab);
  }, [load, tab]);

  const refresh = useCallback(() => void load(tab), [load, tab]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Inbox</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Needs you
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Approvals and suggestions, most urgent first. Suggestions always name their source.
        </p>
      </header>

      <Tabs
        value={tab}
        onChange={(value) => {
          setNotice(null);
          setTab(value as InboxTab);
        }}
        items={[
          { id: "open", label: `Needs you (${openCount})` },
          { id: "done", label: "Done" },
        ]}
      />

      {notice ? (
        <p
          className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 text-sm text-[var(--ink)]"
          role="status"
        >
          {notice}
        </p>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Spinner size="sm" /> Loading inbox…
        </div>
      ) : null}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}{" "}
          <Button size="sm" variant="secondary" onClick={refresh}>
            Retry
          </Button>
        </p>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        tab === "open" ? (
          <EmptyState
            title="Nothing waiting"
            description="When AURA needs a send or change approved, or has a suggestion for you, it appears here and on Today."
          />
        ) : (
          <EmptyState title="No history yet" description="Decided and expired items list here." />
        )
      ) : null}

      {!loading && items.length > 0 ? (
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li key={itemKey(item)}>
              {item.kind === "approval" ? (
                <ApprovalCard approval={item.approval} onDecided={refresh} onReplaced={refresh} />
              ) : (
                <SuggestionCard
                  item={item}
                  onChanged={(message) => {
                    setNotice(message);
                    refresh();
                  }}
                />
              )}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function SuggestionCard({
  item,
  onChanged,
}: {
  item: InboxSuggestionItem;
  onChanged: (message: string) => void;
}) {
  const suggestion = item.suggestion;
  const [busy, setBusy] = useState<"accept" | "dismiss" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dismissing, setDismissing] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [now] = useState(() => Date.now());
  const countdown = suggestion.actionable ? expiresIn(suggestion.expires_at, now) : null;
  const action = suggestion.proposed_action.tool_name;

  async function accept() {
    setError(null);
    setBusy("accept");
    try {
      const result = await acceptSuggestion(suggestion.id);
      onChanged(outcomeMessage(result.outcome, result.summary));
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  async function dismiss() {
    setError(null);
    setBusy("dismiss");
    try {
      await dismissSuggestion(suggestion.id, feedback.trim());
      onChanged("Dismissed. AURA will keep your note in mind.");
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(null);
    }
  }

  return (
    <article
      aria-label={`Suggestion: ${suggestion.title}`}
      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-sm font-semibold text-[var(--ink)]">{suggestion.title}</h2>
        <div className="flex flex-wrap gap-1">
          <Badge tone="accent">Suggestion</Badge>
          {!suggestion.actionable ? (
            <Badge tone={suggestion.status === "accepted" ? "success" : "neutral"}>
              {statusLabel(suggestion.status)}
            </Badge>
          ) : null}
          {countdown ? <Badge tone="warning">expires {countdown}</Badge> : null}
        </div>
      </div>
      {suggestion.reason ? (
        <p className="mt-2 text-sm text-[var(--ink)]">{suggestion.reason}</p>
      ) : null}
      <p className="mt-2 text-xs text-[var(--muted)]">Source: {suggestion.source}</p>
      {action ? (
        <p className="mt-1 text-xs text-[var(--muted)]">
          If you accept, AURA will use <code>{action}</code>; anything that sends or changes data
          still needs your approval first.
        </p>
      ) : null}
      {suggestion.status === "accepted" && suggestion.outcome ? (
        <p className="mt-2 text-xs text-[var(--muted)]">{outcomeMessage(suggestion.outcome)}</p>
      ) : null}
      {suggestion.status === "dismissed" && suggestion.feedback ? (
        <p className="mt-2 text-xs text-[var(--muted)]">Your note: {suggestion.feedback}</p>
      ) : null}

      {error ? (
        <p className="mt-2 text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}

      {suggestion.actionable ? (
        dismissing ? (
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <Input
              aria-label="Why dismiss (optional)"
              placeholder="Why? (optional)"
              value={feedback}
              maxLength={500}
              onChange={(event) => setFeedback(event.target.value)}
            />
            <Button
              size="sm"
              variant="secondary"
              disabled={busy !== null}
              onClick={() => void dismiss()}
            >
              {busy === "dismiss" ? "Dismissing…" : "Confirm dismiss"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={busy !== null}
              onClick={() => setDismissing(false)}
            >
              Cancel
            </Button>
          </div>
        ) : (
          <div className="mt-3 flex flex-wrap gap-2">
            <Button size="sm" disabled={busy !== null} onClick={() => void accept()}>
              {busy === "accept" ? "Accepting…" : "Accept"}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={busy !== null}
              onClick={() => setDismissing(true)}
            >
              Dismiss
            </Button>
          </div>
        )
      ) : null}
    </article>
  );
}
