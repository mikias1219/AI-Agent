"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import { googlePreview, type Event, type File, type Message } from "@/lib/mocks/google";
import { paginate } from "@/lib/pagination";
import { formatWhen } from "../format";
import { GoogleSubnav, isGoogleApp, type GoogleApp } from "./google-subnav";

const PAGE_SIZE = 8;

const rowClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3";

function PagedRows<T extends { id: string }>({
  items,
  page,
  onPageChange,
  render,
}: {
  items: T[];
  page: number;
  onPageChange: (page: number) => void;
  render: (item: T) => ReactNode;
}) {
  const pages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), pages);
  const paged = paginate(items, safePage, PAGE_SIZE);
  if (paged.total === 0) {
    return <EmptyState title="No sample rows" description="This preview list is empty." />;
  }
  return (
    <>
      <ul className="flex flex-col gap-2">{paged.items.map((item) => render(item))}</ul>
      <Pagination
        page={paged.page}
        pageSize={paged.pageSize}
        total={paged.total}
        onPageChange={onPageChange}
      />
    </>
  );
}

function gmailRow(message: Message) {
  return (
    <li key={message.id} className={rowClass}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-[var(--ink)]">{message.subject}</p>
        <time className="text-xs text-[var(--muted)]" dateTime={message.receivedAt}>
          {formatWhen(message.receivedAt)}
        </time>
      </div>
      <p className="mt-1 text-xs text-[var(--muted)]">{message.from}</p>
      <p className="mt-2 text-sm text-[var(--ink)]">{message.snippet}</p>
    </li>
  );
}

function calendarRow(event: Event) {
  return (
    <li key={event.id} className={rowClass}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-[var(--ink)]">{event.title}</p>
        <time className="text-xs text-[var(--muted)]" dateTime={event.startsAt}>
          {formatWhen(event.startsAt)}
        </time>
      </div>
      <p className="mt-1 text-xs text-[var(--muted)]">{event.location}</p>
    </li>
  );
}

function driveRow(file: File) {
  return (
    <li key={file.id} className={rowClass}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-sm font-medium text-[var(--ink)]">{file.name}</p>
        <time className="text-xs text-[var(--muted)]" dateTime={file.updatedAt}>
          {formatWhen(file.updatedAt)}
        </time>
      </div>
      <p className="mt-1 text-xs text-[var(--muted)]">{file.kind}</p>
    </li>
  );
}

export function GooglePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("app");
  const app: GoogleApp = isGoogleApp(requested) ? requested : "gmail";
  const [page, setPage] = useState(1);

  function select(next: GoogleApp) {
    setPage(1);
    const params = new URLSearchParams(searchParams.toString());
    params.set("app", next);
    router.replace(`/connections/google?${params.toString()}`, { scroll: false });
  }

  const title = app === "gmail" ? "Gmail" : app === "calendar" ? "Calendar" : "Drive";

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-5">
      <header>
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
          Google
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">
          One Google app at a time. These rows are samples until the integration exists.
        </p>
      </header>

      <div
        className="rounded-[var(--radius)] border border-[#f9dbaf] bg-[#fef3eb] px-4 py-3"
        role="status"
      >
        <p className="text-sm font-medium text-[var(--ink)]">Integration pending</p>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Gmail, Calendar, and Drive are not connected. Nothing on this page is read from or
          written to Google.
        </p>
      </div>

      <GoogleSubnav value={app} onChange={select} />

      <div
        role="tabpanel"
        aria-labelledby={`tab-${app}`}
        id={`panel-${app}`}
        className="flex flex-col gap-3"
      >
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-[var(--ink)]">{title}</h2>
          <Badge tone="neutral">Preview</Badge>
        </div>
        {app === "gmail" ? (
          <PagedRows items={googlePreview.gmail} page={page} onPageChange={setPage} render={gmailRow} />
        ) : null}
        {app === "calendar" ? (
          <PagedRows
            items={googlePreview.calendar}
            page={page}
            onPageChange={setPage}
            render={calendarRow}
          />
        ) : null}
        {app === "drive" ? (
          <PagedRows items={googlePreview.drive} page={page} onPageChange={setPage} render={driveRow} />
        ) : null}
      </div>
    </div>
  );
}
