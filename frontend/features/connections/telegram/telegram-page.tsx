"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { Spinner } from "@/components/ui/spinner";
import { paginate } from "@/lib/pagination";
import { formatWhen, telegramEventDetail, telegramEventLabel } from "../format";
import { TelegramStatusPanel } from "./telegram-status-panel";
import { useTelegram } from "./use-telegram";

const PAGE_SIZE = 8;

export function TelegramPage() {
  const { status, activity, loading, error, refresh } = useTelegram();
  const [page, setPage] = useState(1);
  const pageCount = Math.max(1, Math.ceil(activity.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount);
  const paged = paginate(activity, safePage, PAGE_SIZE);

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <Link
            href="/connections"
            className="text-xs font-medium text-[var(--accent)] hover:underline"
          >
            All channels
          </Link>
          <h1
            className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Telegram
          </h1>
          <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
            See whether the agent is connected and what it did in your chats.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => void refresh()} disabled={loading}>
          Refresh
        </Button>
      </header>

      {error ? (
        <div className="flex flex-col items-start gap-3">
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
          <Button variant="secondary" size="sm" onClick={() => void refresh({ initial: !status })}>
            Try again
          </Button>
        </div>
      ) : null}

      {loading && !status ? (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-[var(--muted)]">
          <Spinner size="sm" />
          Loading Telegram…
        </div>
      ) : null}

      {status ? <TelegramStatusPanel status={status} /> : null}

      {status || activity.length > 0 ? (
        <section className="flex flex-col gap-3">
          <div>
            <h2 className="text-base font-semibold text-[var(--ink)]">Recent activity</h2>
            <p className="mt-1 text-xs text-[var(--muted)]">
              Replies and skipped messages from your allowlisted chats.
            </p>
          </div>
          {!loading && !error && activity.length === 0 ? (
            <EmptyState
              title="Waiting for your first message"
              description='Message the bot from an allowlisted chat. Questions get replies; casual "ok/thanks" stay quiet.'
            />
          ) : null}
          {activity.length > 0 ? (
            <>
              <ul className="flex flex-col gap-2">
                {paged.items.map((event) => {
                  const detail = telegramEventDetail(event.details);
                  return (
                    <li
                      key={event.id}
                      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3"
                    >
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-sm font-medium text-[var(--ink)]">
                          {telegramEventLabel(event.event)}
                        </p>
                        <time className="text-xs text-[var(--muted)]" dateTime={event.occurred_at}>
                          {formatWhen(event.occurred_at)}
                        </time>
                      </div>
                      <p className="mt-1 text-xs text-[var(--muted)]">
                        {[detail, event.actor].filter(Boolean).join(" · ")}
                      </p>
                    </li>
                  );
                })}
              </ul>
              <Pagination
                page={paged.page}
                pageSize={paged.pageSize}
                total={paged.total}
                onPageChange={setPage}
              />
            </>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
