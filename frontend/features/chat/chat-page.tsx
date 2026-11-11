"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { listConversations, listMessages, sendChat } from "@/lib/api/chat";
import { listApprovals } from "@/lib/api/approvals";
import { cancelRun, followRun, runsUnavailable, startRun } from "@/lib/api/runs";
import type { Approval, ApprovalDecisionResponse } from "@/lib/api/types";
import { Composer } from "./composer";
import { MessageList, type ChatBubble } from "./message-list";
import { emptyRunView, applyRunEvent, isStreamOver, type RunView } from "./run-trail";
import { RuntimeChip } from "./runtime-chip";

export function ChatPage() {
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [stopping, setStopping] = useState(false);
  const runIdRef = useRef<string | null>(null);
  const stopRequestedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [loadKey, setLoadKey] = useState(0);
  const generation = useRef(0);
  const sendAbortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  // Folded event view per assistant bubble, so a paused run can continue where it stopped.
  const viewsRef = useRef(new Map<string, RunView>());

  useEffect(() => {
    return () => {
      sendAbortRef.current?.abort();
      sendAbortRef.current = null;
    };
  }, []);

  useEffect(() => {
    const current = ++generation.current;
    if (sendAbortRef.current) {
      sendAbortRef.current.abort();
      sendAbortRef.current = null;
      setSending(false);
    }
    setLoading(true);
    setError(null);

    listConversations(50)
      .then(async (conversations) => {
        if (current !== generation.current) return;
        const latest = conversations.find((item) => item.user_id === "dashboard");
        if (!latest) {
          setSessionId(null);
          setMessages([]);
          return;
        }
        const history = await listMessages(latest.id);
        // Runs still waiting for the owner (even across an API restart) show their card.
        const waiting = await listApprovals()
          .then((rows) =>
            rows.filter((row) => row.actionable && row.run_id && row.session_id === latest.id),
          )
          .catch(() => [] as Approval[]);
        if (current !== generation.current) return;
        setSessionId(latest.id);
        viewsRef.current.clear();
        setMessages([
          ...history
            .filter((item) => (item.role === "user" || item.role === "assistant") && item.content)
            .map((item) => ({
              id: crypto.randomUUID(),
              role: item.role as "user" | "assistant",
              content: item.content,
            })),
          ...waiting.map((approval) => ({
            id: crypto.randomUUID(),
            role: "assistant" as const,
            content: "",
            runId: approval.run_id ?? undefined,
            approval,
          })),
        ]);
      })
      .catch((err: unknown) => {
        if (current !== generation.current) return;
        setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (current === generation.current) setLoading(false);
      });
  }, [loadKey]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [messages, loading]);

  function newConversation() {
    generation.current += 1;
    sendAbortRef.current?.abort();
    sendAbortRef.current = null;
    setSessionId(null);
    setMessages([]);
    setError(null);
    setSending(false);
    setStopping(false);
    runIdRef.current = null;
    viewsRef.current.clear();
    setLoading(false);
  }

  async function onStop() {
    setStopping(true);
    stopRequestedRef.current = true;
    const runId = runIdRef.current;
    if (!runId) return; // the run is still being created; it is cancelled as soon as it exists
    try {
      await cancelRun(runId);
    } catch (err) {
      setStopping(false);
      setError(apiErrorMessage(err));
    }
  }

  async function runWithSteps(
    text: string,
    gen: number,
    assistantId: string,
    signal: AbortSignal,
  ): Promise<boolean> {
    let run;
    try {
      run = await startRun({ text, sessionId: sessionId ?? undefined });
    } catch (err) {
      if (runsUnavailable(err)) return false; // older backend: use /api/chat instead
      throw err;
    }
    runIdRef.current = run.id;
    if (gen === generation.current) setSessionId(run.session_id);
    if (stopRequestedRef.current) await cancelRun(run.id);

    const view = await follow(run.id, gen, assistantId, signal);
    if (gen !== generation.current) return true;
    if (!isStreamOver(view)) {
      throw new Error("The connection ended before the agent finished.");
    }
    if (view.status === "failed") throw new Error(view.error || "The agent could not finish.");
    return true;
  }

  /** Fold a run's event stream into one assistant bubble until the server closes it. */
  async function follow(
    runId: string,
    gen: number,
    assistantId: string,
    signal: AbortSignal,
  ): Promise<RunView> {
    let view = viewsRef.current.get(assistantId) ?? emptyRunView;
    await followRun(runId, {
      signal,
      after: view.lastSeq,
      onEvent: (event) => {
        view = applyRunEvent(view, event);
        viewsRef.current.set(assistantId, view);
        if (gen !== generation.current) return;
        const current = view;
        setMessages((prev) =>
          prev.map((item) =>
            item.id === assistantId
              ? {
                  ...item,
                  runId,
                  content: current.content,
                  steps: current.steps,
                  pending: !isStreamOver(current),
                  stopped: current.status === "cancelled",
                  approval: current.status === "awaiting_approval" ? current.approval : undefined,
                }
              : item,
          ),
        );
      },
    });
    return view;
  }

  /** The owner decided on a card: continue the run's stream (it resumed on the server). */
  async function onApprovalDecided(messageId: string, response: ApprovalDecisionResponse) {
    const runId = response.run_id;
    setMessages((prev) =>
      prev.map((item) =>
        item.id === messageId ? { ...item, approval: undefined, pending: Boolean(runId) } : item,
      ),
    );
    if (!runId) return;
    const gen = generation.current;
    sendAbortRef.current?.abort();
    const controller = new AbortController();
    sendAbortRef.current = controller;
    setSending(true);
    setError(null);
    try {
      const view = await follow(runId, gen, messageId, controller.signal);
      if (gen !== generation.current) return;
      if (!isStreamOver(view)) throw new Error("The connection ended before the agent finished.");
      if (view.status === "failed") throw new Error(view.error || "The agent could not finish.");
    } catch (err) {
      if (gen !== generation.current) return;
      if (!(err instanceof Error && err.name === "AbortError")) setError(apiErrorMessage(err));
      setMessages((prev) =>
        prev.map((item) => (item.id === messageId ? { ...item, pending: false } : item)),
      );
    } finally {
      if (sendAbortRef.current === controller) {
        sendAbortRef.current = null;
        if (gen === generation.current) setSending(false);
      }
    }
  }

  function onApprovalReplaced(messageId: string, replacement: Approval) {
    setMessages((prev) =>
      prev.map((item) => (item.id === messageId ? { ...item, approval: replacement } : item)),
    );
  }

  async function onSend(text: string) {
    const gen = generation.current;
    sendAbortRef.current?.abort();
    const controller = new AbortController();
    sendAbortRef.current = controller;
    const userId = crypto.randomUUID();
    const assistantId = crypto.randomUUID();
    setError(null);
    stopRequestedRef.current = false;
    setSending(true);
    setMessages((prev) => [
      ...prev,
      { id: userId, role: "user", content: text },
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);

    try {
      if (await runWithSteps(text, gen, assistantId, controller.signal)) return;
      const result = await sendChat(
        { message: text, sessionId: sessionId ?? undefined },
        {
          signal: controller.signal,
          onDelta: (delta) => {
            if (gen !== generation.current) return;
            setMessages((prev) =>
              prev.map((item) =>
                item.id === assistantId ? { ...item, content: item.content + delta } : item,
              ),
            );
          },
        },
      );
      if (gen !== generation.current) return;
      setSessionId(result.session_id);
      setMessages((prev) =>
        prev.map((item) =>
          item.id === assistantId ? { ...item, content: result.reply, pending: false } : item,
        ),
      );
    } catch (err) {
      if (gen !== generation.current) return;
      if (err instanceof Error && err.name === "AbortError") {
        setMessages((prev) => prev.filter((item) => item.id !== userId && item.id !== assistantId));
        return;
      }
      setError(apiErrorMessage(err));
      setMessages((prev) =>
        prev.flatMap((item) => {
          if (item.id !== assistantId) return [item];
          if (!item.content) return [];
          return [{ ...item, pending: false, incomplete: true }];
        }),
      );
    } finally {
      if (sendAbortRef.current === controller) {
        sendAbortRef.current = null;
        runIdRef.current = null;
        if (gen === generation.current) {
          setSending(false);
          setStopping(false);
        }
      }
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100dvh-12.5rem)] min-h-[28rem] w-full max-w-3xl flex-col">
      <header className="mb-4">
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Chat</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Talk with your agent
        </h1>
      </header>

      <section className="flex min-h-0 flex-1 flex-col rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
        <div className="min-h-0 flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex h-full items-center justify-center gap-2 text-sm text-[var(--muted)]">
              <Spinner size="sm" />
              Loading conversation…
            </div>
          ) : null}

          {!loading && error && messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <p className="text-sm text-[var(--danger)]" role="alert">
                {error}
              </p>
              <Button variant="secondary" size="sm" onClick={() => setLoadKey((key) => key + 1)}>
                Try again
              </Button>
            </div>
          ) : null}

          {!loading && !error && messages.length === 0 ? (
            <EmptyState
              title="Start a conversation"
              description="Ask a question or describe what you want done."
            />
          ) : null}

          {messages.length > 0 ? (
            <MessageList
              messages={messages}
              onApprovalDecided={(id, response) => void onApprovalDecided(id, response)}
              onApprovalReplaced={onApprovalReplaced}
            />
          ) : null}
          <div ref={bottomRef} />
        </div>

        {error && messages.length > 0 ? (
          <p className="mt-3 text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}

        <Composer
          disabled={loading}
          sending={sending}
          stopping={stopping}
          onSend={onSend}
          onStop={onStop}
          onNewConversation={newConversation}
        />
        <RuntimeChip />
      </section>
    </div>
  );
}
