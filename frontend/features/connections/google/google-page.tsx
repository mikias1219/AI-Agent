"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Pagination } from "@/components/ui/pagination";
import {
  connectGoogle,
  disconnectGoogle,
  getGoogleStatus,
  listCalendar,
  listDrive,
  listGmail,
  type GoogleEvent,
  type GoogleFile,
  type GoogleMessage,
  type GoogleStatus,
} from "@/lib/api/google";
import { apiErrorMessage } from "@/lib/api/client";
import { capabilities } from "@/lib/capabilities";
import { googlePreview } from "@/lib/mocks/google";
import { paginate } from "@/lib/pagination";
import { formatWhen } from "../format";
import { GoogleSubnav, isGoogleApp, type GoogleApp } from "./google-subnav";

const PAGE_SIZE = 8;

const rowClass =
  "rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3";

function PagedRows<T extends { id: string }>({
  items,
  page,
  total,
  onPageChange,
  render,
  emptyTitle,
  emptyDescription,
}: {
  items: T[];
  page: number;
  total: number;
  onPageChange: (page: number) => void;
  render: (item: T) => ReactNode;
  emptyTitle: string;
  emptyDescription: string;
}) {
  if (total === 0) {
    return <EmptyState title={emptyTitle} description={emptyDescription} />;
  }
  return (
    <>
      <ul className="flex flex-col gap-2">{items.map((item) => render(item))}</ul>
      <Pagination page={page} pageSize={PAGE_SIZE} total={total} onPageChange={onPageChange} />
    </>
  );
}

function gmailRow(message: GoogleMessage) {
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

function calendarRow(event: GoogleEvent) {
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

function driveRow(file: GoogleFile) {
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
  const useApi = capabilities.google === "api";
  const [status, setStatus] = useState<GoogleStatus | null>(null);
  const [items, setItems] = useState<GoogleMessage[] | GoogleEvent[] | GoogleFile[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function select(next: GoogleApp) {
    setPage(1);
    const params = new URLSearchParams(searchParams.toString());
    params.set("app", next);
    router.replace(`/connections/google?${params.toString()}`, { scroll: false });
  }

  const refreshStatus = useCallback(async () => {
    if (!useApi) return;
    try {
      setStatus(await getGoogleStatus());
    } catch (err) {
      setError(apiErrorMessage(err));
    }
  }, [useApi]);

  const loadList = useCallback(async () => {
    if (!useApi) {
      if (app === "gmail") {
        const paged = paginate(googlePreview.gmail, page, PAGE_SIZE);
        setItems(paged.items);
        setTotal(paged.total);
      } else if (app === "calendar") {
        const paged = paginate(googlePreview.calendar, page, PAGE_SIZE);
        setItems(paged.items);
        setTotal(paged.total);
      } else {
        const paged = paginate(googlePreview.drive, page, PAGE_SIZE);
        setItems(paged.items);
        setTotal(paged.total);
      }
      return;
    }
    if (!status?.connected) {
      setItems([]);
      setTotal(0);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result =
        app === "gmail"
          ? await listGmail(page, PAGE_SIZE)
          : app === "calendar"
            ? await listCalendar(page, PAGE_SIZE)
            : await listDrive(page, PAGE_SIZE);
      setItems(result.items);
      setTotal(result.total);
    } catch (err) {
      setError(apiErrorMessage(err));
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [app, page, status?.connected, useApi]);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  async function onConnect() {
    setBusy(true);
    setError("");
    try {
      const res = await connectGoogle();
      if (res.auth_url) {
        window.location.assign(res.auth_url);
      }
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function onDisconnect() {
    setBusy(true);
    setError("");
    try {
      await disconnectGoogle();
      await refreshStatus();
      setItems([]);
      setTotal(0);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const title = app === "gmail" ? "Gmail" : app === "calendar" ? "Calendar" : "Drive";
  const connected = Boolean(status?.connected);

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
          One Google app at a time. Gmail shows Important mail (up to 100). Calendar shows upcoming
          events. Drive lists recent files.
        </p>
      </header>

      {useApi ? (
        <div
          className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
          role="status"
        >
          <div>
            <p className="text-sm font-medium text-[var(--ink)]">
              {connected
                ? `Connected${status?.email ? ` as ${status.email}` : ""}`
                : "Not connected"}
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {status?.oauth_configured
                ? connected
                  ? "Live rows load from your Google account."
                  : "Start Google consent to store tokens on the server."
                : "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env first."}
            </p>
          </div>
          <div className="flex gap-2">
            {connected ? (
              <Button
                type="button"
                variant="secondary"
                disabled={busy}
                onClick={() => void onDisconnect()}
              >
                Disconnect
              </Button>
            ) : (
              <Button
                type="button"
                disabled={busy || !status?.oauth_configured}
                onClick={() => void onConnect()}
              >
                Connect Google
              </Button>
            )}
          </div>
        </div>
      ) : (
        <div
          className="rounded-[var(--radius)] border border-[#f9dbaf] bg-[#fef3eb] px-4 py-3"
          role="status"
        >
          <p className="text-sm font-medium text-[var(--ink)]">Integration pending</p>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Gmail, Calendar, and Drive are preview samples until the integration is enabled.
          </p>
        </div>
      )}

      {error ? (
        <p className="text-sm text-[var(--danger)]" role="alert">
          {error}
        </p>
      ) : null}

      <GoogleSubnav value={app} onChange={select} />

      <div
        role="tabpanel"
        aria-labelledby={`tab-${app}`}
        id={`panel-${app}`}
        className="flex flex-col gap-3"
      >
        <div className="flex items-center gap-2">
          <h2 className="text-base font-semibold text-[var(--ink)]">{title}</h2>
          <Badge tone={useApi && connected ? "success" : "neutral"}>
            {useApi && connected ? "Live" : "Preview"}
          </Badge>
        </div>
        {loading ? <p className="text-sm text-[var(--muted)]">Loading…</p> : null}
        {!loading && app === "gmail" ? (
          <PagedRows
            items={items as GoogleMessage[]}
            page={page}
            total={total}
            onPageChange={setPage}
            render={gmailRow}
            emptyTitle={connected ? "No messages" : "Connect Google"}
            emptyDescription={
              connected
                ? "No Important messages in this window."
                : "Connect to load Important Gmail."
            }
          />
        ) : null}
        {!loading && app === "calendar" ? (
          <PagedRows
            items={items as GoogleEvent[]}
            page={page}
            total={total}
            onPageChange={setPage}
            render={calendarRow}
            emptyTitle={connected ? "No events" : "Connect Google"}
            emptyDescription={
              connected
                ? "No upcoming events in this window."
                : "Connect to load upcoming Calendar."
            }
          />
        ) : null}
        {!loading && app === "drive" ? (
          <PagedRows
            items={items as GoogleFile[]}
            page={page}
            total={total}
            onPageChange={setPage}
            render={driveRow}
            emptyTitle={connected ? "No files" : "Connect Google"}
            emptyDescription={connected ? "No Drive files on this page." : "Connect to load Drive."}
          />
        ) : null}
      </div>
    </div>
  );
}
