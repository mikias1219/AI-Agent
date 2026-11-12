"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { listConversations, listMessages, sendChat } from "@/lib/api/chat";
import { listApprovals } from "@/lib/api/approvals";
import { cancelRun, followRun, runsUnavailable, startRun } from "@/lib/api/runs";
import type { Approval, ApprovalDecisionResponse, ConversationSummary } from "@/lib/api/types";
import { groupThreads, threadTitle } from "./chat-cards-logic";
import { Composer } from "./composer";
import { MessageList, type ChatBubble } from "./message-list";
import { emptyRunView, applyRunEvent, isStreamOver, type RunView } from "./run-trail";
import { RuntimeChip } from "./runtime-chip";

export function ChatPage({ initialPrompt = "" }: { initialPrompt?: string }) {
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [stopping, setStopping] = useState(false);
  const runIdRef = useRef<string | null>(null);
  const stopRequestedRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [loadKey, setLoadKey] = useState(0);
  const [threads, setThreads] = useState<ConversationSummary[]>([]);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [threadsError, setThreadsError] = useState<string | null>(null);
  const [titles, setTitles] = useState<Record<string, string>>({});
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

  /** Load one session's messages (and any runs still waiting for the owner). */
  async function openSession(sessionKey: string, current: number) {
    const history = await listMessages(sessionKey);
    // Runs still waiting for the owner (even across an API restart) show their card.
    const waiting = await listApprovals()
      .then((rows) =>
        rows.filter((row) => row.actionable && row.run_id && row.session_id === sessionKey),
      )
      .catch(() => [] as Approval[]);
    if (current !== generation.current) return;
    setSessionId(sessionKey);
    viewsRef.current.clear();
    const visible = history.filter(
      (item) => (item.role === "user" || item.role === "assistant") && item.content,
    );
    const firstUser = visible.find((item) => item.role === "user");
    if (firstUser) setTitles((prev) => ({ ...prev, [sessionKey]: firstUser.content }));
    setMessages([
      ...visible.map((item) => ({
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
  }

  function resetForSwitch(): number {
    const current = ++generation.current;
    sendAbortRef.current?.abort();
    sendAbortRef.current = null;
    runIdRef.current = null;
    stopRequestedRef.current = false;
    setSending(false);
    setStopping(false);
    setError(null);
    return current;
  }

  function selectThread(id: string) {
    if (id === sessionId) return;
    const current = resetForSwitch();
    setLoading(true);
    setMessages([]);
    openSession(id, current)
      .catch((err: unknown) => {
        if (current !== generation.current) return;
        setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (current === generation.current) setLoading(false);
      });
  }

  useEffect(() => {
    const current = ++generation.current;
    if (sendAbortRef.current) {
      sendAbortRef.current.abort();
      sendAbortRef.current = null;
      setSending(false);
    }
    setLoading(true);
    setThreadsLoading(true);
    setThreadsError(null);
    setError(null);

    listConversations(50)
      .then(async (conversations) => {
        if (current !== generation.current) return;
        const mine = conversations.filter((item) => item.user_id === "dashboard");
        setThreads(mine);
        setThreadsLoading(false);
        const latest = mine[0];
        if (!latest) {
          setSessionId(null);
          setMessages([]);
          return;
        }
        await openSession(latest.id, current);
      })
      .catch((err: unknown) => {
        if (current !== generation.current) return;
        const message = apiErrorMessage(err);
        setThreadsError(message);
        setThreadsLoading(false);
        setError(message);
      })
      .finally(() => {
        if (current === generation.current) setLoading(false);
      });
  }, [loadKey]);

  // A first message starts a new session: refresh the list so the thread shows up.
  useEffect(() => {
    if (!sessionId || sending || threads.some((item) => item.id === sessionId)) return;
    let cancelled = false;
    listConversations(50)
      .then((conversations) => {
        if (!cancelled) setThreads(conversations.filter((item) => item.user_id === "dashboard"));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [sessionId, sending, threads]);

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
                  memoryProposal: current.memoryProposal,
                  usedMemories: current.usedMemories,
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
    if (sessionId) {
      setTitles((prev) => (prev[sessionId] ? prev : { ...prev, [sessionId]: text }));
    }
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
    <div className="mx-auto flex h-[calc(100dvh-12.5rem)] min-h-[28rem] w-full max-w-5xl flex-col">
      <header className="mb-4">
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Chat</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Talk with your agent
        </h1>
      </header>

      <div className="flex min-h-0 flex-1 flex-col gap-4 md:flex-row">
        <ThreadList
          threads={threads}
          titles={titles}
          activeId={sessionId}
          loading={threadsLoading}
          error={threadsError}
          onSelect={selectThread}
          onNew={newConversation}
          onRetry={() => setLoadKey((key) => key + 1)}
        />
        <section className="flex min-h-0 min-w-0 flex-1 flex-col rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-4 sm:p-5">
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
            initialText={initialPrompt}
            onSend={onSend}
            onStop={onStop}
            onNewConversation={newConversation}
          />
          <RuntimeChip />
        </section>
      </div>
    </div>
  );
}

type ThreadListProps = {
  threads: ConversationSummary[];
  titles: Record<string, string>;
  activeId: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRetry: () => void;
};

function ThreadList({
  threads,
  titles,
  activeId,
  loading,
  error,
  onSelect,
  onNew,
  onRetry,
}: ThreadListProps) {
  const groups = groupThreads(threads);
  return (
    <aside
      aria-label="Conversations"
      className="flex max-h-40 shrink-0 flex-col rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 md:max-h-none md:w-60"
    >
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Chats</p>
        <Button variant="ghost" size="sm" onClick={onNew}>
          New chat
        </Button>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading ? (
          <p className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <Spinner size="sm" />
            Loading chats…
          </p>
        ) : null}
        {!loading && error ? (
          <div className="flex flex-col items-start gap-2">
            <p className="text-sm text-[var(--danger)]" role="alert">
              {error}
            </p>
            <Button variant="secondary" size="sm" onClick={onRetry}>
              Try again
            </Button>
          </div>
        ) : null}
        {!loading && !error && threads.length === 0 ? (
          <p className="text-sm text-[var(--muted)]">No chats yet. Send a message to start one.</p>
        ) : null}
        {!loading && !error
          ? groups.map((group) => (
              <section key={group.label} className="mb-3">
                <h2 className="mb-1 text-[11px] font-medium tracking-wide text-[var(--muted)] uppercase">
                  {group.label}
                </h2>
                <ul className="flex flex-col gap-1">
                  {group.items.map((thread) => {
                    const active = thread.id === activeId;
                    return (
                      <li key={thread.id}>
                        <button
                          type="button"
                          aria-current={active ? "true" : undefined}
                          onClick={() => onSelect(thread.id)}
                          className={`w-full truncate rounded-[var(--radius)] px-2 py-1.5 text-left text-sm transition ${
                            active
                              ? "bg-[var(--accent-soft)] font-medium text-[var(--accent)]"
                              : "text-[var(--ink)] hover:bg-[var(--canvas)]"
                          }`}
                        >
                          {threadTitle(titles[thread.id], thread.created_at)}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))
          : null}
      </div>
    </aside>
  );
}
