"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { listConversations, listMessages, sendChat } from "@/lib/api/chat";
import { Composer } from "./composer";
import { MessageList, type ChatBubble } from "./message-list";

export function ChatPage() {
  const [messages, setMessages] = useState<ChatBubble[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadKey, setLoadKey] = useState(0);
  const generation = useRef(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const current = ++generation.current;
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
        if (current !== generation.current) return;
        setSessionId(latest.id);
        setMessages(
          history
            .filter((item) => (item.role === "user" || item.role === "assistant") && item.content)
            .map((item) => ({
              id: crypto.randomUUID(),
              role: item.role as "user" | "assistant",
              content: item.content,
            })),
        );
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
    setSessionId(null);
    setMessages([]);
    setError(null);
    setLoading(false);
  }

  async function onSend(text: string) {
    const assistantId = crypto.randomUUID();
    setError(null);
    setSending(true);
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", content: text },
      { id: assistantId, role: "assistant", content: "", pending: true },
    ]);

    try {
      const result = await sendChat(
        { message: text, sessionId: sessionId ?? undefined },
        {
          onDelta: (delta) => {
            setMessages((prev) =>
              prev.map((item) =>
                item.id === assistantId ? { ...item, content: item.content + delta } : item,
              ),
            );
          },
        },
      );
      setSessionId(result.session_id);
      setMessages((prev) =>
        prev.map((item) =>
          item.id === assistantId ? { ...item, content: result.reply, pending: false } : item,
        ),
      );
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      setError(apiErrorMessage(err));
      setMessages((prev) =>
        prev.flatMap((item) => {
          if (item.id !== assistantId) return [item];
          if (!item.content) return [];
          return [{ ...item, pending: false, incomplete: true }];
        }),
      );
    } finally {
      setSending(false);
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

          {messages.length > 0 ? <MessageList messages={messages} /> : null}
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
          onSend={onSend}
          onNewConversation={newConversation}
        />
      </section>
    </div>
  );
}
