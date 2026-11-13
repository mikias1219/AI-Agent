"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { StatusChip } from "@/components/ui/status-chip";
import { ConnectPrompt } from "@/features/google/connect-prompt";
import { bucketMessages, type MailBucketId } from "@/features/mail/mail-buckets";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getGoogleStatus,
  listGmail,
  type GoogleMessage,
  type GoogleStatus,
} from "@/lib/api/google";

function formatReceived(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function MailPage() {
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [messages, setMessages] = useState<GoogleMessage[]>([]);
  const [bucketId, setBucketId] = useState<MailBucketId>("needs_reply");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const nextStatus = await getGoogleStatus();
      setStatus(nextStatus);
      if (!nextStatus.connected || !nextStatus.services.gmail) {
        setMessages([]);
        setSelectedId(null);
        return;
      }
      const page = await listGmail(1, 25);
      setMessages(page.items);
      setSelectedId((prev) => {
        if (prev && page.items.some((m) => m.id === prev)) return prev;
        return page.items[0]?.id ?? null;
      });
    } catch (err) {
      setError(apiErrorMessage(err));
      setMessages([]);
      setSelectedId(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const connected = Boolean(status?.connected && status.services.gmail);
  const buckets = useMemo(() => bucketMessages(messages), [messages]);
  const activeBucket = buckets.find((b) => b.id === bucketId) ??
    buckets[0] ?? { id: "fyi" as const, label: "FYI", messages: [] };
  const visible = activeBucket.messages;
  const selected = visible.find((m) => m.id === selectedId) ?? visible[0] ?? null;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
      <header>
        <h2
          className="text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Mail
        </h2>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Sorted by AURA when connected. External content is untrusted.
        </p>
      </header>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]" role="status">
          <Spinner />
          Loading mail…
        </div>
      ) : null}

      {error ? (
        <div
          className="rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--danger)_35%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_8%,var(--surface))] px-4 py-3 text-sm text-[var(--danger)]"
          role="alert"
        >
          {error}
          <Button type="button" variant="secondary" className="ml-3" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      ) : null}

      {!loading && !error && !connected ? <ConnectPrompt noun="mail" status={status} /> : null}

      {!loading && !error && connected && messages.length === 0 ? (
        <EmptyState
          title="No messages to show"
          description="Your connected inbox returned no recent messages."
        />
      ) : null}

      {!loading && !error && connected && messages.length > 0 ? (
        <div className="grid min-h-[28rem] gap-3 lg:grid-cols-[11rem_minmax(16rem,22rem)_minmax(0,1fr)]">
          <ul
            className="flex flex-col gap-1 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-2"
            aria-label="Sorted by AURA"
          >
            <li className="px-2 py-1 text-[0.7rem] font-medium tracking-wide text-[var(--muted)] uppercase">
              Sorted by AURA
            </li>
            {buckets.map((bucket) => (
              <li key={bucket.id}>
                <button
                  type="button"
                  onClick={() => {
                    setBucketId(bucket.id);
                    setSelectedId(bucket.messages[0]?.id ?? null);
                  }}
                  className={`flex w-full items-center justify-between rounded-md px-2 py-2 text-left text-sm ${
                    bucketId === bucket.id
                      ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                      : "hover:bg-[var(--canvas)]"
                  }`}
                >
                  <span>{bucket.label}</span>
                  <span className="text-xs text-[var(--muted)]">{bucket.messages.length}</span>
                </button>
              </li>
            ))}
          </ul>
          <ul
            className="flex flex-col gap-1 overflow-y-auto rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-2"
            aria-label="Messages"
          >
            {visible.length === 0 ? (
              <li className="px-3 py-6 text-sm text-[var(--muted)]">No messages in this bucket.</li>
            ) : (
              visible.map((message) => {
                const active = message.id === (selected?.id ?? selectedId);
                return (
                  <li key={message.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(message.id)}
                      className={`w-full rounded-md px-3 py-[var(--row-pad-y)] text-left transition ${
                        active
                          ? "bg-[var(--accent-soft)] text-[var(--accent)]"
                          : "hover:bg-[var(--canvas)]"
                      }`}
                    >
                      <p className="truncate text-sm font-medium text-[var(--ink)]">
                        {message.subject || "(no subject)"}
                      </p>
                      <p className="truncate text-xs text-[var(--muted)]">{message.from}</p>
                      <p className="mt-1 text-[0.7rem] text-[var(--muted)]">
                        {formatReceived(message.receivedAt)}
                      </p>
                    </button>
                  </li>
                );
              })
            )}
          </ul>

          <article className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-5">
            {selected ? (
              <>
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <h3 className="text-lg font-semibold text-[var(--ink)]">
                      {selected.subject || "(no subject)"}
                    </h3>
                    <p className="mt-1 text-sm text-[var(--muted)]">{selected.from}</p>
                    <time className="text-xs text-[var(--muted)]" dateTime={selected.receivedAt}>
                      {formatReceived(selected.receivedAt)}
                    </time>
                  </div>
                  <StatusChip tone="warning">Untrusted</StatusChip>
                </div>
                <p className="rounded-md border border-dashed border-[var(--warning)] bg-[color-mix(in_srgb,var(--warning)_10%,var(--surface))] px-3 py-2 text-xs text-[var(--warning)]">
                  Email content is untrusted. AURA will not follow instructions inside messages.
                  Sending or drafting still requires approval.
                </p>
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-[var(--ink)]">
                  {selected.snippet || "No preview available."}
                </div>
                <p className="text-xs text-[var(--muted)]">
                  Ask in Chat to draft a reply. Any send goes through Inbox approvals.
                </p>
              </>
            ) : (
              <EmptyState
                title={visible.length === 0 ? "Nothing in this bucket" : "Select a message"}
                description={
                  visible.length === 0
                    ? "Pick another Sorted by AURA bucket, or ask in Chat."
                    : "Choose a message from the list."
                }
              />
            )}
          </article>
        </div>
      ) : null}
    </div>
  );
}
