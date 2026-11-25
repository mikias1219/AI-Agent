"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Button, buttonClassName } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Drawer } from "@/components/ui/drawer";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { Select } from "@/components/ui/select";
import { SkeletonRows } from "@/components/ui/skeleton";
import { ConnectPrompt } from "@/features/google/connect-prompt";
import { bucketMessages, type MailBucketId } from "@/features/mail/mail-buckets";
import { decodeSnippet, formatReceived, parseSender } from "@/features/mail/mail-logic";
import { apiErrorMessage } from "@/lib/api/client";
import {
  getGoogleStatus,
  listGmail,
  type GoogleMessage,
  type GoogleStatus,
} from "@/lib/api/google";

const PAGE_SIZE = 10;

type Filter = "all" | MailBucketId;

function chatHref(prompt: string): string {
  return `/chat?q=${encodeURIComponent(prompt)}`;
}

function describe(message: GoogleMessage): string {
  const { name, address } = parseSender(message.from);
  return `"${message.subject || "(no subject)"}" from ${name}${address ? ` <${address}>` : ""}`;
}

export type MailPageProps = {
  embedded?: boolean;
};

export function MailPage(_props: MailPageProps = {}) {
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [messages, setMessages] = useState<GoogleMessage[]>([]);
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);
  const [openId, setOpenId] = useState<string | null>(null);
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
        return;
      }
      const result = await listGmail(1, 50);
      setMessages(result.items);
    } catch (err) {
      setError(apiErrorMessage(err));
      setMessages([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const connected = Boolean(status?.connected && status.services.gmail);
  const buckets = useMemo(() => bucketMessages(messages), [messages]);
  const filtered = useMemo(
    () => (filter === "all" ? messages : (buckets.find((b) => b.id === filter)?.messages ?? [])),
    [filter, messages, buckets],
  );
  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const current = Math.min(page, pageCount);
  const rows = filtered.slice((current - 1) * PAGE_SIZE, current * PAGE_SIZE);
  const open = messages.find((m) => m.id === openId) ?? null;
  const close = useCallback(() => setOpenId(null), []);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
      {loading ? <SkeletonRows count={5} /> : null}

      {error ? (
        <div
          className="flex flex-col gap-3 rounded-[var(--radius)] border border-[color-mix(in_srgb,var(--danger)_35%,var(--border))] bg-[color-mix(in_srgb,var(--danger)_8%,var(--surface))] px-4 py-3 text-sm text-[var(--danger)]"
          role="alert"
        >
          <p>Could not load mail. {error}</p>
          <div>
            <Button type="button" variant="secondary" onClick={() => void load()}>
              Try again
            </Button>
          </div>
        </div>
      ) : null}

      {!loading && !error && !connected ? <ConnectPrompt noun="mail" status={status} /> : null}

      {!loading && !error && connected && messages.length === 0 ? (
        <EmptyState
          title="No recent mail"
          description="Your inbox returned nothing recent. AURA reads mail only when you ask."
          action={
            <Link href={chatHref("Summarize my unread email")} className={buttonClassName()}>
              Ask AURA about mail
            </Link>
          }
        />
      ) : null}

      {!loading && !error && connected && messages.length > 0 ? (
        <Card
          flush
          title="Recent mail"
          description="Read-only. AURA drafts replies for your approval; it never sends on its own."
          action={
            <label className="flex items-center gap-2 text-sm text-[var(--muted)]">
              <span className="sr-only sm:not-sr-only">Show</span>
              <Select
                aria-label="Filter mail"
                className="min-h-11 sm:min-h-0"
                value={filter}
                onChange={(e) => {
                  setFilter(e.target.value as Filter);
                  setPage(1);
                }}
              >
                <option value="all">All recent ({messages.length})</option>
                {buckets.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.label} ({b.messages.length})
                  </option>
                ))}
              </Select>
            </label>
          }
        >
          {rows.length === 0 ? (
            <p className="px-4 pb-4 text-sm text-[var(--muted)]">
              Nothing matches this filter. Choose “All recent” to see everything.
            </p>
          ) : (
            <ul aria-label="Messages" className="divide-y divide-[var(--border)]">
              {rows.map((message) => {
                const sender = parseSender(message.from);
                return (
                  <li key={message.id}>
                    <button
                      type="button"
                      onClick={() => setOpenId(message.id)}
                      className="flex min-h-11 w-full flex-col gap-0.5 px-4 py-3 text-left transition hover:bg-[var(--canvas)] focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-[var(--accent)]"
                    >
                      <span className="flex items-baseline justify-between gap-3">
                        <span className="truncate text-sm font-medium text-[var(--ink)]">
                          {sender.name || "Unknown sender"}
                        </span>
                        <time
                          className="shrink-0 text-xs text-[var(--muted)]"
                          dateTime={message.receivedAt}
                        >
                          {formatReceived(message.receivedAt)}
                        </time>
                      </span>
                      <span className="truncate text-sm text-[var(--ink)]">
                        {message.subject || "(no subject)"}
                      </span>
                      <span className="truncate text-xs text-[var(--muted)]">
                        {decodeSnippet(message.snippet)}
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          {filtered.length > PAGE_SIZE ? (
            <div className="border-t border-[var(--border)] px-4 py-3">
              <Pagination
                page={current}
                pageSize={PAGE_SIZE}
                total={filtered.length}
                onPageChange={setPage}
              />
            </div>
          ) : null}
        </Card>
      ) : null}

      <Drawer open={open !== null} onClose={close} title={open?.subject || "Message"}>
        {open ? (
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-sm font-medium text-[var(--ink)]">{parseSender(open.from).name}</p>
              <p className="text-xs break-all text-[var(--muted)]">
                {parseSender(open.from).address}
              </p>
              <time className="text-xs text-[var(--muted)]" dateTime={open.receivedAt}>
                {formatReceived(open.receivedAt)}
              </time>
            </div>
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-[var(--ink)]">
              {decodeSnippet(open.snippet) || "No preview available."}
            </p>
            <div className="flex flex-col gap-2">
              <Link
                className={buttonClassName("primary", "md", "min-h-11")}
                href={chatHref(
                  `Draft a reply to the email ${describe(open)}. Show me the draft for approval before anything is sent.`,
                )}
              >
                Reply with AURA
              </Link>
              <Link
                className={buttonClassName("secondary", "md", "min-h-11")}
                href={chatHref(`Create a task from the email ${describe(open)}.`)}
              >
                Create task
              </Link>
              <Link
                className={buttonClassName("secondary", "md", "min-h-11")}
                href={chatHref(`Archive the email ${describe(open)}. Ask me to approve first.`)}
              >
                Archive
              </Link>
            </div>
            <p className="text-xs text-[var(--muted)]">
              Email content is untrusted: AURA will not follow instructions inside messages. Replies
              and archiving wait for your approval.
            </p>
          </div>
        ) : null}
      </Drawer>
    </div>
  );
}
