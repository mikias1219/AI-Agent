"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { Spinner } from "@/components/ui/spinner";
import { apiErrorMessage } from "@/lib/api/client";
import { demoChat, demoCreateTask, openDemoSession, type DemoSession } from "@/lib/api/demo";

export function DemoPage() {
  const [session, setSession] = useState<DemoSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState("What should I do today?");
  const [reply, setReply] = useState<string | null>(null);
  const [chatSession, setChatSession] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    openDemoSession()
      .then((data) => {
        if (!cancelled) setSession(data);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(apiErrorMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function ask() {
    setBusy(true);
    setError(null);
    try {
      const result = await demoChat(prompt, chatSession);
      setChatSession(result.session_id);
      setReply(result.reply);
      const refreshed = await openDemoSession();
      setSession(refreshed);
    } catch (err: unknown) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function addTask() {
    setBusy(true);
    setError(null);
    try {
      await demoCreateTask("Demo follow-up");
      setSession(await openDemoSession());
    } catch (err: unknown) {
      setError(apiErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--canvas)] text-[var(--ink)]">
      <div className="border-b border-[var(--accent)] bg-[var(--accent-soft)] px-4 py-3 text-center text-sm">
        <strong>Demo mode</strong> — simulated workspace. External actions are labeled SIMULATED and
        never mix with real accounts.{" "}
        <Link href="/login" className="underline">
          Sign in for your workspace
        </Link>
      </div>

      <main className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
        <header>
          <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">AURA</p>
          <h1
            className="mt-2 text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Try the safe-by-design agent
          </h1>
          <p className="mt-2 text-sm text-[var(--muted)]">
            Seeded tasks and memories. Chat uses a scripted provider; sends and deletes stay
            simulated.
          </p>
        </header>

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
            <Spinner size="sm" />
            Opening demo workspace…
          </div>
        ) : null}

        {error ? (
          <p className="text-sm text-[var(--danger)]" role="alert">
            {error}
          </p>
        ) : null}

        {!loading && session ? (
          <>
            <section className="flex flex-col gap-3">
              <h2 className="text-base font-semibold">Ask AURA</h2>
              <textarea
                className="min-h-24 w-full rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] p-3 text-sm"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <Button onClick={ask} disabled={busy || !prompt.trim()}>
                  {busy ? "Working…" : "Send"}
                </Button>
                <Button variant="secondary" onClick={addTask} disabled={busy}>
                  Add demo task
                </Button>
              </div>
              {reply ? (
                <pre className="overflow-auto rounded-[var(--radius)] bg-[var(--surface)] p-3 text-sm whitespace-pre-wrap">
                  {reply}
                </pre>
              ) : null}
            </section>

            <section>
              <h2 className="text-base font-semibold">Seeded tasks</h2>
              {session.tasks.length === 0 ? (
                <EmptyState title="No tasks" description="Create one with Add demo task." />
              ) : (
                <ul className="mt-2 flex flex-col gap-2">
                  {session.tasks.map((task) => (
                    <li
                      key={task.id}
                      className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
                    >
                      {task.title}{" "}
                      <span className="text-xs text-[var(--muted)]">({task.status})</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section>
              <h2 className="text-base font-semibold">Seeded memories</h2>
              <ul className="mt-2 flex flex-col gap-2">
                {session.memories.map((memory) => (
                  <li
                    key={memory.id}
                    className="rounded-[var(--radius)] border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm"
                  >
                    <span className="text-xs text-[var(--muted)] uppercase">{memory.kind}</span>
                    <p className="mt-1">{memory.content}</p>
                  </li>
                ))}
              </ul>
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
