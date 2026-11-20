"use client";

import { FormEvent, KeyboardEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { StatusChip } from "@/components/ui/status-chip";
import { Textarea } from "@/components/ui/textarea";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { ChatCards, cardsFromSteps } from "@/features/chat/chat-cards";
import { stepLabel } from "@/features/chat/run-trail";
import { useAgentRun } from "@/features/chat/use-agent-run";

export type QuickAskDrawerProps = {
  open: boolean;
  onClose: () => void;
};

/** Side drawer for a one-off question. Same run stream and cards as Chat. */
export function QuickAskDrawer({ open, onClose }: QuickAskDrawerProps) {
  const [text, setText] = useState("");
  const run = useAgentRun();
  const latestStep = run.view.steps.at(-1);
  const cards = cardsFromSteps(run.view.steps);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(() => document.getElementById("quick-ask-input")?.focus(), 220);
    return () => window.clearTimeout(id);
  }, [open]);

  useEffect(() => {
    if (!open) run.reset();
    // Reset only when the drawer closes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function submit() {
    const question = text.trim();
    if (!question || run.busy) return;
    setText("");
    await run.start(question);
  }

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
            disabled={run.busy}
          />
          <div className="flex items-center justify-between gap-2">
            <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
              Enter to send · Shift+Enter for a new line
            </p>
            <Button type="submit" size="sm" disabled={!text.trim()} loading={run.busy}>
              <Send className="h-4 w-4" aria-hidden />
              Ask
            </Button>
          </div>
        </form>

        {run.question ? (
          <section
            aria-live="polite"
            aria-label="Quick ask result"
            className="flex flex-col gap-3 rounded-[var(--radius)] border border-[var(--border)] bg-[var(--canvas)] p-3"
          >
            <p className="text-[length:var(--text-caption)] text-[var(--muted)]">You asked</p>
            <p className="text-[length:var(--text-body)] whitespace-pre-wrap text-[var(--ink)]">
              {run.question}
            </p>

            {run.busy ? (
              <StatusChip tone="accent">
                {latestStep ? `Working: ${stepLabel(latestStep.name)}…` : "Working…"}
              </StatusChip>
            ) : null}

            {run.view.approval ? (
              <ApprovalCard
                approval={run.view.approval}
                onDecided={() => {
                  /* Durable pause: continue in Chat or Needs you. */
                }}
              />
            ) : run.view.status === "awaiting_approval" ? (
              <div className="flex flex-col gap-2">
                <StatusChip tone="warning">Waiting for your approval</StatusChip>
                <Link
                  href="/inbox"
                  onClick={onClose}
                  className="text-[length:var(--text-body)] text-[var(--accent)] underline-offset-2 hover:underline"
                >
                  Review it in Needs you
                </Link>
              </div>
            ) : null}

            {run.view.content ? (
              <p className="text-[length:var(--text-body)] whitespace-pre-wrap text-[var(--ink)]">
                {run.view.content}
              </p>
            ) : null}

            <ChatCards cards={cards} />

            {run.view.status === "cancelled" ? (
              <StatusChip tone="neutral">Stopped</StatusChip>
            ) : null}

            {run.error ? (
              <p role="alert" className="text-[length:var(--text-body)] text-[var(--danger)]">
                {run.error}
              </p>
            ) : null}

            {!run.busy && run.view.status === "completed" ? (
              <div className="flex flex-wrap gap-3">
                <Link
                  href={
                    run.sessionId ? `/chat?session=${encodeURIComponent(run.sessionId)}` : "/chat"
                  }
                  onClick={onClose}
                  className="text-[length:var(--text-caption)] text-[var(--accent)] underline-offset-2 hover:underline"
                >
                  Continue in Chat
                </Link>
                <Link
                  href="/activity"
                  onClick={onClose}
                  className="text-[length:var(--text-caption)] text-[var(--accent)] underline-offset-2 hover:underline"
                >
                  See Activity
                </Link>
              </div>
            ) : null}
          </section>
        ) : (
          <p className="text-[length:var(--text-body)] text-[var(--muted)]">
            Ask a quick question or give AURA a small job. Cards and approvals use the same run
            stream as Chat.
          </p>
        )}
      </div>
    </Drawer>
  );
}
