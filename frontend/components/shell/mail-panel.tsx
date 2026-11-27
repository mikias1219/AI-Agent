"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, ListPlus, PenLine, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { StatusChip } from "@/components/ui/status-chip";
import { Tabs } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/toast";
import { useAgentRun } from "@/features/chat/use-agent-run";
import { bucketMessages } from "@/features/mail/mail-buckets";
import { decodeSnippet, formatReceived, parseSender } from "@/features/mail/mail-logic";
import { apiErrorMessage } from "@/lib/api/client";
import { getGoogleStatus, listGmail, type GoogleMessage } from "@/lib/api/google";
import { createTask } from "@/lib/api/tasks";
import { askingCount, gmailLink } from "./mail-panel-logic";

const PAGE_SIZE = 20;

type MailState =
  | { kind: "loading" }
  | { kind: "disconnected" }
  | { kind: "error"; message: string }
  | { kind: "ready"; messages: GoogleMessage[] };

// Kept between openings so the panel paints at once; refreshed in the background.
let lastMessages: GoogleMessage[] | null = null;

export type MailPanelProps = {
  open: boolean;
  onClose: () => void;
  /** Reports the asking count so the top bar can badge the mail icon. */
  onCount?: (count: number) => void;
};

/**
 * Mail in a side panel over any page: newest messages, a filter for the ones that ask you
 * something, and per message: draft a reply with the agent (never sent), make a task, or open
 * it in Gmail. Read-only Google access is enough.
 */
export function MailPanel({ open, onClose, onCount }: MailPanelProps) {
  const { toast } = useToast();
  const [state, setState] = useState<MailState>(
    lastMessages ? { kind: "ready", messages: lastMessages } : { kind: "loading" },
  );
  const [filter, setFilter] = useState<"asking" | "all">("all");
  const [selected, setSelected] = useState<GoogleMessage | null>(null);
  const run = useAgentRun();

  const load = useCallback(async () => {
    try {
      const status = await getGoogleStatus();
      if (!status.connected || !status.services.gmail) {
        setState({ kind: "disconnected" });
        onCount?.(0);
        return;
      }
      const page = await listGmail(1, PAGE_SIZE);
      lastMessages = page.items;
      setState({ kind: "ready", messages: page.items });
      onCount?.(askingCount(page.items));
    } catch (err) {
      if (!lastMessages) setState({ kind: "error", message: apiErrorMessage(err) });
    }
  }, [onCount]);

  useEffect(() => {
    if (open) void load();
  }, [open, load]);

  // A quiet check shortly after the app loads, so the top-bar badge is right before opening.
  useEffect(() => {
    const id = window.setTimeout(() => void load(), 4000);
    return () => window.clearTimeout(id);
  }, [load]);

  useEffect(() => {
    if (!open) {
      setSelected(null);
      run.reset();
    }
    // Reset only when the panel closes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function draftReply(message: GoogleMessage) {
    const sender = parseSender(message.from);
    await run.start(
      `Draft a reply to ${sender.name || sender.address} about “${message.subject}”.`,
      undefined,
      [
        "The user is reading this email in the Mail panel and wants a reply drafted.",
        `Gmail message id: ${message.id}. From: ${message.from}. Subject: ${message.subject}.`,
        `Preview: ${decodeSnippet(message.snippet).slice(0, 600)}`,
        "Draft only. Do not send anything. No email signature.",
        "Show the draft text; offer to save it as a Gmail draft if that tool is available.",
      ].join("\n"),
    );
  }

  async function makeTask(message: GoogleMessage) {
    const sender = parseSender(message.from);
    try {
      await createTask({ title: `Reply to ${sender.name || sender.address}: ${message.subject}` });
      window.dispatchEvent(new Event("compass:data-changed"));
      toast("Task added to today.", "success");
    } catch (err) {
      toast(apiErrorMessage(err), "danger");
    }
  }

  const messages = state.kind === "ready" ? state.messages : [];
  const asking = bucketMessages([...messages]).find((b) => b.id === "needs_reply")?.messages ?? [];
  const shown = filter === "asking" ? asking : messages;

  return (
    <Drawer open={open} onClose={onClose} title="Mail">
      {selected ? (
        <div className="flex flex-col gap-4">
          <button
            type="button"
            onClick={() => {
              setSelected(null);
              run.reset();
            }}
            className="inline-flex min-h-9 items-center gap-1.5 self-start text-sm font-medium text-[var(--accent)] hover:underline"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            All mail
          </button>
          <div className="flex flex-col gap-1">
            <h3 className="text-base font-semibold text-[var(--ink)]">{selected.subject}</h3>
            <p className="text-sm text-[var(--muted)]">
              {parseSender(selected.from).name || parseSender(selected.from).address} ·{" "}
              {formatReceived(selected.receivedAt)}
            </p>
          </div>
          <p className="rounded-[var(--radius)] bg-[var(--subtle)] p-3 text-sm whitespace-pre-wrap text-[var(--ink)]">
            {decodeSnippet(selected.snippet)}
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => void draftReply(selected)} loading={run.busy}>
              <PenLine className="h-4 w-4" aria-hidden />
              Draft a reply
            </Button>
            <Button size="sm" variant="secondary" onClick={() => void makeTask(selected)}>
              <ListPlus className="h-4 w-4" aria-hidden />
              Make a task
            </Button>
            <a
              href={gmailLink(selected.id)}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-9 items-center gap-1.5 rounded-[var(--radius)] px-2 text-sm font-medium text-[var(--accent)] hover:underline"
            >
              Open in Gmail
              <ExternalLink className="h-3.5 w-3.5" aria-hidden />
            </a>
          </div>
          {run.question ? (
            <section aria-live="polite" className="flex flex-col gap-2">
              {run.busy ? <StatusChip tone="accent">Drafting…</StatusChip> : null}
              {run.view.content ? (
                <div className="rounded-[var(--radius)] border border-[var(--border)] p-3 text-sm whitespace-pre-wrap text-[var(--ink)]">
                  {run.view.content}
                </div>
              ) : null}
              {run.error ? (
                <p role="alert" className="text-sm text-[var(--danger)]">
                  {run.error}
                </p>
              ) : null}
              <p className="text-xs text-[var(--muted)]">
                Nothing is sent. Copy the draft, or ask the agent to save it in Gmail.
              </p>
            </section>
          ) : null}
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {state.kind === "disconnected" ? (
            <div className="flex flex-col items-start gap-2 text-sm">
              <p className="text-[var(--ink)]">Gmail is not connected.</p>
              <Link
                href="/connections/google"
                onClick={onClose}
                className="font-medium text-[var(--accent)] hover:underline"
              >
                Connect Google
              </Link>
            </div>
          ) : state.kind === "error" ? (
            <div className="flex flex-col items-start gap-2 text-sm" role="alert">
              <p className="text-[var(--danger)]">Mail could not be loaded: {state.message}</p>
              <Button size="sm" variant="secondary" onClick={() => void load()}>
                Try again
              </Button>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between gap-2">
                <Tabs
                  variant="quiet"
                  aria-label="Mail filter"
                  value={filter}
                  onChange={(id) => setFilter(id as "asking" | "all")}
                  items={[
                    { id: "all", label: `All ${messages.length || ""}`.trim() },
                    { id: "asking", label: `Asks you ${asking.length || ""}`.trim() },
                  ]}
                />
                <button
                  type="button"
                  onClick={() => void load()}
                  aria-label="Refresh mail"
                  className="inline-flex h-9 w-9 items-center justify-center rounded-[var(--radius)] text-[var(--muted)] hover:bg-[var(--hover)] hover:text-[var(--ink)]"
                >
                  <RefreshCw className="h-4 w-4" aria-hidden />
                </button>
              </div>
              {state.kind === "loading" ? (
                <p className="text-sm text-[var(--muted)]">Loading mail…</p>
              ) : shown.length === 0 ? (
                <p className="text-sm text-[var(--muted)]">
                  {filter === "asking" ? "Nothing asks you something right now." : "No mail."}
                </p>
              ) : (
                <ul className="flex flex-col divide-y divide-[var(--border)]">
                  {shown.map((message) => {
                    const sender = parseSender(message.from);
                    return (
                      <li key={message.id}>
                        <button
                          type="button"
                          onClick={() => setSelected(message)}
                          className="flex w-full flex-col gap-0.5 rounded-[var(--radius-sm)] px-1 py-2.5 text-left hover:bg-[var(--hover)]"
                        >
                          <span className="flex items-baseline justify-between gap-2">
                            <span className="truncate text-sm font-semibold text-[var(--ink)]">
                              {sender.name || sender.address}
                            </span>
                            <span className="shrink-0 text-xs text-[var(--muted)]">
                              {formatReceived(message.receivedAt)}
                            </span>
                          </span>
                          <span className="truncate text-sm text-[var(--ink)]">
                            {message.subject}
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
            </>
          )}
        </div>
      )}
    </Drawer>
  );
}
