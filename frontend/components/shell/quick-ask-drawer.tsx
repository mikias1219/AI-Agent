"use client";

import { FormEvent, KeyboardEvent, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { StatusChip } from "@/components/ui/status-chip";
import { Textarea } from "@/components/ui/textarea";
import { applyRunEvent, emptyRunView, stepLabel, type RunView } from "@/features/chat/run-trail";
import { apiErrorMessage } from "@/lib/api/client";
import { followRun, startRun } from "@/lib/api/runs";

export type QuickAskDrawerProps = {
  open: boolean;
  onClose: () => void;
};

type Ask = { text: string; view: RunView; error: string | null; busy: boolean };

/** Side drawer for a one-off question. Same run gate as chat: POST /api/runs, then stream events. */
export function QuickAskDrawer({ open, onClose }: QuickAskDrawerProps) {
  const [text, setText] = useState("");
  const [ask, setAsk] = useState<Ask | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => document.getElementById("quick-ask-input")?.focus(), 220);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const submit = useCallback(async () => {
    const question = text.trim();
    if (!question || ask?.busy) return;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setText("");
    setAsk({ text: question, view: emptyRunView, error: null, busy: true });
    try {
      const run = await startRun({ text: question });
      let view = emptyRunView;
      await followRun(run.id, {
        signal: controller.signal,
        onEvent: (event) => {
          view = applyRunEvent(view, event);
          setAsk((prev) => (prev ? { ...prev, view } : prev));
        },
      });
      if (view.status === "running") {
        throw new Error("The connection ended before the agent finished.");
      }
      setAsk((prev) =>
        prev
          ? { ...prev, busy: false, error: view.status === "failed" ? (view.error ?? null) : null }
          : prev,
      );
    } catch (err) {
      if (controller.signal.aborted) return;
      setAsk((prev) => (prev ? { ...prev, busy: false, error: apiErrorMessage(err) } : prev));
    }
  }, [ask?.busy, text]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void submit();
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  const view = ask?.view;
  const latestStep = view?.steps.at(-1);

  return (
    <Drawer open={open} onClose={onClose} title="Quick ask">
      <div className="flex h-full flex-col gap-4">
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <label className="sr-only" htmlFor="quick-ask-input">
            Ask AURA
          </label>
          <Textarea
            id="quick-ask-input"
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={onKeyDown}
            maxLength={10000}
            rows={3}
            placeholder="Ask AURA anything…"
            disabled={ask?.busy}
          />
          <div className="flex items-center justify-between gap-2">
            <p className="text-xs text-[var(--muted)]">
              Enter to send · Shift+Enter for a new line
            </p>
            <Button type="submit" size="sm" disabled={!text.trim()} loading={ask?.busy}>
              <Send className="h-4 w-4" aria-hidden />
              Ask
            </Button>
          </div>
        </form>

        {ask ? (
          <section
            aria-live="polite"
            aria-label="Quick ask result"
            className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] p-3"
          >
            <p className="text-xs text-[var(--muted)]">You asked</p>
            <p className="text-sm whitespace-pre-wrap text-[var(--ink)]">{ask.text}</p>

            {ask.busy ? (
              <StatusChip tone="accent">
                {latestStep ? `Working: ${stepLabel(latestStep.name)}…` : "Working…"}
              </StatusChip>
            ) : null}

            {view?.status === "awaiting_approval" ? (
              <div className="flex flex-col gap-2">
                <StatusChip tone="warning">Waiting for your approval</StatusChip>
                <Link
                  href="/inbox"
                  onClick={onClose}
                  className="text-sm text-[var(--accent)] underline-offset-2 hover:underline"
                >
                  Review it in Inbox
                </Link>
              </div>
            ) : null}

            {view?.content ? (
              <p className="text-sm whitespace-pre-wrap text-[var(--ink)]">{view.content}</p>
            ) : null}

            {view?.status === "cancelled" ? <StatusChip tone="neutral">Stopped</StatusChip> : null}

            {ask.error ? (
              <p role="alert" className="text-sm text-[var(--danger)]">
                {ask.error}
              </p>
            ) : null}

            {!ask.busy && view?.status === "completed" ? (
              <Link
                href="/activity"
                onClick={onClose}
                className="text-xs text-[var(--accent)] underline-offset-2 hover:underline"
              >
                See what happened in Activity
              </Link>
            ) : null}
          </section>
        ) : (
          <p className="text-sm text-[var(--muted)]">
            Ask a quick question or give AURA a small job. Anything that needs your OK will wait in
            Inbox.
          </p>
        )}
      </div>
    </Drawer>
  );
}
