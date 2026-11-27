"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowUp, Sparkles, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Drawer } from "@/components/ui/drawer";
import { StatusChip } from "@/components/ui/status-chip";
import { Textarea } from "@/components/ui/textarea";
import { ApprovalCard } from "@/features/approvals/approval-card";
import { ChatCards, cardsFromSteps } from "@/features/chat/chat-cards";
import { stepLabel } from "@/features/chat/run-trail";
import { useAgentRun } from "@/features/chat/use-agent-run";
import {
  agentContext,
  cleanQuestion,
  insightLine,
  MAX_QUESTION_CHARS,
  MODULE_AGENTS,
  type ModuleId,
} from "./module-agent-config";

/** Window event a page sends to ask its own agent: `detail` = { module, text, context? }. */
export const AGENT_ASK_EVENT = "compass:agent-ask";
export type AgentAskDetail = {
  module: ModuleId;
  text: string;
  context?: string;
  /** false: open the panel with the text ready to edit instead of sending it. */
  send?: boolean;
};

export function askModuleAgent(detail: AgentAskDetail): void {
  window.dispatchEvent(new CustomEvent<AgentAskDetail>(AGENT_ASK_EVENT, { detail }));
}

type Turn = { question: string; answer: string };

export type ModuleAgentProps = {
  module: ModuleId;
  /** One line from the page's own data, e.g. "Food is at 86% of budget with 9 days left". */
  insight?: string | null;
  /** One action next to the insight; omit to show only "Ask". */
  action?: { label: string; onClick: () => void } | null;
  /** Called after a run finishes so the page can reload what the agent may have changed. */
  onDataChanged?: () => void;
};

/**
 * The agent bar under a page header, and the module's agent panel. Ctrl/Cmd + J opens the
 * panel. Answers stream with the same cards, approvals and Undo toasts as Chat.
 */
export function ModuleAgent({ module, insight, action, onDataChanged }: ModuleAgentProps) {
  const config = MODULE_AGENTS[module];
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [asked, setAsked] = useState<string | null>(null);
  const [turns, setTurns] = useState<Turn[]>([]);
  const run = useAgentRun();
  const changedRef = useRef(onDataChanged);
  changedRef.current = onDataChanged;
  const cards = cardsFromSteps(run.view.steps);
  const latestStep = run.view.steps.at(-1);

  useEffect(() => {
    function onKey(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "j") {
        event.preventDefault();
        setOpen(true);
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!open) return;
    const id = window.setTimeout(
      () => document.getElementById(`agent-input-${module}`)?.focus(),
      220,
    );
    return () => window.clearTimeout(id);
  }, [open, module]);

  async function ask(raw: string, extraContext?: string) {
    const question = cleanQuestion(raw);
    if (!question || run.busy) return;
    // Keep the finished answer on screen as history before starting the next one.
    if (asked && run.view.content) {
      setTurns((prev) => [...prev, { question: asked, answer: run.view.content }].slice(-6));
    }
    setText("");
    setAsked(question);
    setOpen(true);
    const view = await run.start(
      question,
      run.sessionId ?? undefined,
      agentContext(module, extraContext),
    );
    if (view && view.steps.length > 0) changedRef.current?.();
  }

  // Pages can ask their own agent (e.g. Learn's "Get new words") without leaving the page.
  const askRef = useRef(ask);
  askRef.current = ask;
  useEffect(() => {
    function onAsk(event: Event) {
      const detail = (event as CustomEvent<AgentAskDetail>).detail;
      if (detail?.module !== module) return;
      if (detail.send === false) {
        setText(detail.text);
        setOpen(true);
        return;
      }
      void askRef.current(detail.text, detail.context);
    }
    window.addEventListener(AGENT_ASK_EVENT, onAsk);
    return () => window.removeEventListener(AGENT_ASK_EVENT, onAsk);
  }, [module]);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void ask(text);
  }

  function onKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void ask(text);
    }
  }

  return (
    <>
      <section
        aria-label={config.name}
        className="flex min-h-[48px] flex-wrap items-center gap-x-3 gap-y-2 rounded-[var(--radius-lg,var(--radius))] border border-[color-mix(in_srgb,var(--accent)_35%,var(--border))] bg-[color-mix(in_srgb,var(--accent)_7%,var(--surface))] px-4 py-2"
      >
        <Sparkles className="h-4 w-4 shrink-0 text-[var(--accent-strong)]" aria-hidden />
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="min-w-0 flex-1 truncate text-left text-[length:var(--text-body)] text-[var(--ink)] hover:underline focus-visible:underline focus-visible:outline-none"
          title={`Open the ${config.name}`}
        >
          {insightLine(module, insight)}
        </button>
        <div className="flex shrink-0 items-center gap-1">
          {action ? (
            <Button size="sm" variant="ghost" onClick={action.onClick}>
              {action.label}
            </Button>
          ) : null}
          <Button size="sm" variant="secondary" onClick={() => setOpen(true)}>
            Ask
            <kbd className="ml-1.5 hidden rounded border border-[var(--border)] px-1 text-[10px] text-[var(--muted)] lg:inline">
              Ctrl J
            </kbd>
          </Button>
        </div>
      </section>

      <Drawer open={open} onClose={() => setOpen(false)} title={config.name}>
        <div className="flex h-full flex-col gap-4">
          <p className="text-[length:var(--text-caption)] text-[var(--muted)]">
            Knows your {config.scope}. Anything that pays, sends or deletes asks you first.
          </p>

          <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto" aria-live="polite">
            {turns.map((turn, index) => (
              <div key={index} className="flex flex-col gap-2">
                <p className="self-end rounded-[var(--radius)] bg-[var(--subtle)] px-3 py-2 text-[length:var(--text-body)] text-[var(--ink)]">
                  {turn.question}
                </p>
                <p className="text-[length:var(--text-body)] whitespace-pre-wrap text-[var(--ink)]">
                  {turn.answer}
                </p>
              </div>
            ))}

            {asked ? (
              <div className="flex flex-col gap-2">
                <p className="self-end rounded-[var(--radius)] bg-[var(--subtle)] px-3 py-2 text-[length:var(--text-body)] text-[var(--ink)]">
                  {asked}
                </p>
                {run.busy ? (
                  <StatusChip tone="accent">
                    {latestStep ? `Working: ${stepLabel(latestStep.name)}…` : "Working…"}
                  </StatusChip>
                ) : null}
                {run.view.approval ? (
                  <ApprovalCard
                    approval={run.view.approval}
                    onDecided={() => changedRef.current?.()}
                  />
                ) : run.view.status === "awaiting_approval" ? (
                  <Link
                    href="/inbox"
                    className="text-[length:var(--text-body)] text-[var(--accent)] underline-offset-2 hover:underline"
                  >
                    Waiting for your approval in Needs you
                  </Link>
                ) : null}
                {run.view.content ? (
                  <div className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 text-[length:var(--text-body)] whitespace-pre-wrap text-[var(--ink)]">
                    {run.view.content}
                  </div>
                ) : null}
                <ChatCards cards={cards} />
                {run.error ? (
                  <p role="alert" className="text-[length:var(--text-body)] text-[var(--danger)]">
                    {run.error}
                  </p>
                ) : null}
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-[length:var(--text-caption)] font-semibold text-[var(--muted)]">
                  Try
                </p>
                <div className="flex flex-wrap gap-2">
                  {config.chips.map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      onClick={() => void ask(chip)}
                      className="min-h-[36px] rounded-full border border-[var(--border)] px-3 text-[length:var(--text-small)] text-[var(--ink)] transition-colors hover:border-[var(--accent)] hover:bg-[var(--hover)]"
                    >
                      {chip}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <form
            onSubmit={onSubmit}
            className="flex flex-col gap-2 border-t border-[var(--border)] pt-3"
          >
            <label className="sr-only" htmlFor={`agent-input-${module}`}>
              {config.placeholder}
            </label>
            <div className="flex items-end gap-2">
              <Textarea
                id={`agent-input-${module}`}
                value={text}
                onChange={(event) => setText(event.target.value)}
                onKeyDown={onKeyDown}
                maxLength={MAX_QUESTION_CHARS}
                rows={2}
                placeholder={config.placeholder}
                disabled={run.busy}
              />
              {run.busy ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => void run.stop()}
                  aria-label="Stop"
                >
                  <Square className="h-4 w-4" aria-hidden />
                </Button>
              ) : (
                <Button type="submit" disabled={!text.trim()} aria-label="Send">
                  <ArrowUp className="h-4 w-4" aria-hidden />
                </Button>
              )}
            </div>
            {run.sessionId ? (
              <Link
                href={`/chat?session=${encodeURIComponent(run.sessionId)}`}
                className="self-start text-[length:var(--text-caption)] text-[var(--accent)] underline-offset-2 hover:underline"
              >
                Open the full conversation
              </Link>
            ) : null}
          </form>
        </div>
      </Drawer>
    </>
  );
}
