"use client";

import { useCallback, useEffect, useState } from "react";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import { Button, buttonClassName } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { SkeletonRows } from "@/components/ui/skeleton";
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
import {
  actionWords,
  expiresIn,
  itemKey,
  outcomeMessage,
  sourceWords,
  statusLabel,
} from "./inbox-logic";

export type InboxView = "approvals" | "suggestions" | "mail" | "done";

function apiTab(view: InboxView): InboxTab {
  return view === "done" ? "done" : "open";
}

function tabLabel(label: string, count: number): string {
  return count > 0 ? `${label} ${count}` : label;
}

function filterInbox(view: InboxView, items: InboxItem[]): InboxItem[] {
  if (view === "done") return items;
  if (view === "approvals") return items.filter((item) => item.kind === "approval");
  if (view === "mail") {
    return items.filter(
      (item) => item.kind === "suggestion" && item.suggestion.kind === "mail_reply",
    );
  }
  return items.filter(
    (item) => item.kind === "suggestion" && item.suggestion.kind !== "mail_reply",
  );
}

/** The shell header names the page, so this renders tabs and content only. */
export function InboxPage() {
  const [view, setView] = useState<InboxView>("approvals");
  const [picked, setPicked] = useState(false);
  const [counts, setCounts] = useState<Record<InboxView, number>>({
    approvals: 0,
    suggestions: 0,
    mail: 0,
    done: 0,
  });
  const [items, setItems] = useState<InboxItem[]>([]);
  const [openCount, setOpenCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async (next: InboxView) => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getInbox(apiTab(next));
      setItems(filterInbox(next, payload.items));
      setOpenCount(payload.counts.open);
      if (next !== "done") {
        setCounts((prev) => ({
          ...prev,
          approvals: filterInbox("approvals", payload.items).length,
          suggestions: filterInbox("suggestions", payload.items).length,
          mail: filterInbox("mail", payload.items).length,
        }));
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(view);
  }, [load, view]);

  // Open on the first tab that has something waiting, once, unless the owner already chose.
  useEffect(() => {
    if (picked || loading) return;
    setPicked(true);
    if (counts[view] > 0) return;
    const first = (["approvals", "suggestions", "mail"] as const).find((id) => counts[id] > 0);
    if (first) setView(first);
  }, [picked, loading, counts, view]);

  const refresh = useCallback(() => void load(view), [load, view]);

  const panel = (id: InboxView) => (
    <InboxPanel
      view={id}
      openCount={openCount}
      notice={notice}
      loading={loading}
      error={error}
      items={items}
      onRetry={refresh}
      onNotice={(message) => {
        setNotice(message);
        refresh();
      }}
    />
  );

  return (
    <div className="flex flex-col gap-5">
      <Tabs
        aria-label="Inbox"
        value={view}
        onChange={(value) => {
          setPicked(true);
          setNotice(null);
          setView(value as InboxView);
        }}
        items={[
          { id: "approvals", label: tabLabel("Approvals", counts.approvals) },
          { id: "suggestions", label: tabLabel("Suggestions", counts.suggestions) },
          { id: "mail", label: tabLabel("Mail replies", counts.mail) },
          { id: "done", label: "Done" },
        ]}
        panels={{
          approvals: panel("approvals"),
          suggestions: panel("suggestions"),
          mail: panel("mail"),
          done: panel("done"),
        }}
      />
    </div>
  );
}

function InboxPanel({
  view,
  openCount,
  notice,
  loading,
  error,
  items,
  onRetry,
  onNotice,
}: {
  view: InboxView;
  openCount: number;
  notice: string | null;
  loading: boolean;
  error: string | null;
  items: InboxItem[];
  onRetry: () => void;
  onNotice: (message: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      {view === "mail" ? (
        <p className="text-[length:var(--text-small)] text-[var(--muted)]">
          Want every message?{" "}
          <Link href="/mail" className="font-medium text-[var(--accent)] hover:underline">
            Browse all mail
          </Link>
        </p>
      ) : null}

      {view === "approvals" && openCount > 0 ? (
        <p className="text-[length:var(--text-small)] text-[var(--muted)]">
          {openCount} open in Needs you overall
        </p>
      ) : null}

      {notice ? (
        <p
          className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 text-sm text-[var(--ink)]"
          role="status"
        >
          {notice}
        </p>
      ) : null}

      {loading ? <SkeletonRows count={3} /> : null}

      {error ? (
        <div
          className="flex flex-wrap items-center gap-2 text-sm text-[var(--danger)]"
          role="alert"
        >
          <span>{error}</span>
          <Button size="sm" variant="secondary" className="min-h-11" onClick={onRetry}>
            Try again
          </Button>
        </div>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        view === "approvals" ? (
          <EmptyState
            title="Nothing waiting"
            description="When Compass needs a send or change approved, it appears here and on Today."
            action={
              <Link href="/chat" className={buttonClassName("primary")}>
                Ask Compass to do something
              </Link>
            }
          />
        ) : view === "suggestions" ? (
          <EmptyState
            title="No suggestions yet"
            description="Suggestions appear when a routine or briefing proposes something, and always name their source."
            action={
              <Link href="/routines" className={buttonClassName("primary")}>
                Set up a routine
              </Link>
            }
          />
        ) : view === "mail" ? (
          <EmptyState
            title="No mail replies"
            description="Draft replies appear here with a source citation; sending still needs your approval."
            action={
              <Link href="/routines" className={buttonClassName("primary")}>
                Turn on inbox triage
              </Link>
            }
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
                <ApprovalCard
                  compact
                  approval={item.approval}
                  onDecided={onRetry}
                  onReplaced={onRetry}
                />
              ) : (
                <SuggestionCard item={item} onChanged={onNotice} />
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
      onChanged("Dismissed. Compass will keep your note in mind.");
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
        <h3 className="text-sm font-semibold text-[var(--ink)]">{suggestion.title}</h3>
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
      <p className="mt-2 text-xs text-[var(--muted)]">From: {sourceWords(suggestion.source)}</p>
      {action ? (
        <p className="mt-1 text-xs text-[var(--muted)]">
          Accept to {actionWords(action)}. Anything that sends or changes data still asks you first.
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
            <Button
              size="sm"
              className="min-h-11"
              disabled={busy !== null}
              onClick={() => void accept()}
            >
              {busy === "accept" ? "Accepting…" : "Accept"}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              className="min-h-11"
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
