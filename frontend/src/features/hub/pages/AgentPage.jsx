import { useEffect, useRef } from 'react';
import { inferenceLabel, ollamaReachableLabel } from '../../../shared/lib/runtime-status.js';
import { CHANNELS } from '../channels.js';
import { channelPath } from '../routes.js';

const STARTERS = [
  {
    id: 'hello',
    label: 'Say hello',
    text: 'Hi — introduce yourself in one short sentence and ask how you can help today.',
  },
  {
    id: 'day',
    label: 'Plan my day',
    text: 'Help me plan today in three short bullets. Ask one clarifying question first if you need it.',
  },
  {
    id: 'tg',
    label: 'How does Telegram work?',
    text: 'Explain briefly how I chat with you on Telegram from this hub, in plain language.',
  },
];

export default function AgentPage({
  chat,
  prompt,
  setPrompt,
  ask,
  send,
  busy,
  conversations,
  loadConversation,
  newConversation,
  sessionId,
  approvals,
  decide,
  status,
  go,
  name,
}) {
  const bottom = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [chat, busy]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [sessionId]);

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!busy && prompt.trim()) ask(e);
    }
  }

  const pending = (approvals || []).filter((a) => a.actionable);
  const liveChannels = CHANNELS.filter((c) => c.live);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 flex-wrap items-center gap-3 border-b border-slate-200 bg-white px-4 py-3 md:px-5">
        <div className="min-w-0 flex-1">
          <h1 className="text-lg font-semibold text-slate-900">My Agent</h1>
          <p className="text-sm text-slate-500">
            Chat here. The same agent answers on Telegram when the bot is running.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <StatusChip label={inferenceLabel(status)} ok={status?.active_runtime !== 'fake'} />
          <StatusChip
            label={ollamaReachableLabel(status)}
            ok={!!status?.ollama_reachable || status?.provider === 'fake'}
          />
          <button
            type="button"
            disabled={busy}
            onClick={newConversation}
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            New chat
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <aside className="hidden w-56 shrink-0 flex-col border-r border-slate-200 bg-slate-50/80 md:flex lg:w-64">
          <div className="border-b border-slate-200 px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Conversations
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {!conversations.length && (
              <p className="px-2 py-3 text-xs leading-5 text-slate-500">
                Your first chat will show up here. Telegram sessions appear too.
              </p>
            )}
            {conversations.map((c) => {
              const active = sessionId === c.id;
              const origin = c.user_id?.startsWith('telegram:')
                ? 'Telegram'
                : c.user_id === 'dashboard'
                  ? 'Hub'
                  : c.user_id || 'Chat';
              return (
                <button
                  key={c.id}
                  type="button"
                  disabled={busy}
                  onClick={() => loadConversation(c.id)}
                  className={`mb-1 w-full rounded-xl px-3 py-2.5 text-left transition ${
                    active
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-slate-700 hover:bg-white hover:ring-1 hover:ring-slate-200'
                  }`}
                >
                  <span className="block text-sm font-medium">
                    {origin} · {c.id.slice(0, 6)}
                  </span>
                  <span
                    className={`mt-0.5 block text-[11px] ${active ? 'text-indigo-100' : 'text-slate-400'}`}
                  >
                    {new Date(c.created_at).toLocaleString()}
                  </span>
                </button>
              );
            })}
          </div>
          <div className="border-t border-slate-200 p-3">
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
              Live channels
            </p>
            <div className="flex flex-wrap gap-1.5">
              {liveChannels.map((c) => (
                <button
                  key={c.id}
                  type="button"
                  onClick={() => go(channelPath(c.id))}
                  className="inline-flex items-center gap-1.5 rounded-full bg-white px-2 py-1 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200 hover:ring-indigo-300"
                >
                  <span className={`size-1.5 rounded-full ${c.color}`} />
                  {c.name}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col bg-white">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto px-4 py-5 md:px-8">
            {!chat.length && (
              <div className="mx-auto max-w-2xl py-8 text-center md:py-14">
                <div className="mx-auto mb-4 grid size-14 place-items-center rounded-2xl bg-indigo-50 text-indigo-600">
                  <svg
                    viewBox="0 0 24 24"
                    className="h-7 w-7"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                  >
                    <path d="M12 3l2 6h6l-5 4 2 6-5-3.5L7 19l2-6-5-4h6z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {name ? `Hi ${name.split(' ')[0]}` : 'Chat with AURA'}
                </h2>
                <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">
                  Type below or pick a starter. Replies appear in this thread.
                </p>
                <div className="mt-8 flex flex-col gap-2 sm:mx-auto sm:max-w-md">
                  {STARTERS.map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      disabled={busy}
                      onClick={() => send(s.text)}
                      className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-left transition hover:border-indigo-300 hover:bg-indigo-50/50"
                    >
                      <span className="block text-sm font-medium text-slate-900">{s.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {chat
              .filter((m) => m.content || m.streaming)
              .map((m, i) => (
                <div
                  key={`${i}-${m.role}`}
                  className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[min(42rem,92%)] whitespace-pre-wrap break-words rounded-2xl px-4 py-3 text-sm leading-6 ${
                      m.role === 'user'
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-100 text-slate-800 ring-1 ring-slate-200/80'
                    }`}
                  >
                    {m.content || (m.streaming ? '…' : '')}
                    {m.streaming && m.content && (
                      <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-indigo-400 align-middle" />
                    )}
                    {m.incomplete && (
                      <p className="mt-2 text-xs font-medium text-rose-600">
                        Incomplete reply — the model connection failed.
                      </p>
                    )}
                  </div>
                </div>
              ))}

            {busy && !chat.some((m) => m.streaming && !m.content) && (
              <p role="status" className="text-xs font-medium text-indigo-600">
                Agent is working…
              </p>
            )}
            <div ref={bottom} />
          </div>

          {pending.length > 0 && (
            <div className="shrink-0 space-y-2 border-t border-amber-200 bg-amber-50 px-4 py-3 md:px-8">
              {pending.map((a) => (
                <div
                  key={a.id}
                  className="rounded-xl border border-amber-200 bg-white p-3 shadow-sm"
                >
                  <p className="text-sm font-semibold text-slate-900">
                    Approval needed: {a.tool_name}
                  </p>
                  <pre className="mt-2 max-h-28 overflow-auto rounded-lg bg-slate-50 p-2 text-[11px] text-slate-600">
                    {JSON.stringify(a.arguments || a.arguments_json || {}, null, 2)}
                  </pre>
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white"
                      onClick={() => decide(a.id, true)}
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700"
                      onClick={() => decide(a.id, false)}
                    >
                      Deny
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <form
            onSubmit={ask}
            className="shrink-0 border-t border-slate-200 bg-white px-4 py-3 md:px-8 md:py-4"
          >
            <div className="mx-auto flex max-w-3xl gap-2">
              <label className="sr-only" htmlFor="agent-input">
                Message your agent
              </label>
              <textarea
                id="agent-input"
                ref={inputRef}
                rows={2}
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={onKeyDown}
                maxLength={10000}
                placeholder="Ask AURA… (Enter to send, Shift+Enter for a new line)"
                required
                disabled={busy}
                className="min-h-[2.75rem] min-w-0 flex-1 resize-y rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-100"
              />
              <button
                type="submit"
                disabled={busy || !prompt.trim()}
                aria-label="Send message"
                className="self-end rounded-2xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
              >
                Send
              </button>
            </div>
            <p className="mx-auto mt-2 max-w-3xl text-[11px] text-slate-400">
              Channel agents:{' '}
              <button
                type="button"
                className="text-indigo-600 hover:underline"
                onClick={() => go('dashboard')}
              >
                Dashboard
              </button>
              {' · '}
              <button
                type="button"
                className="text-indigo-600 hover:underline"
                onClick={() => go(channelPath('telegram'))}
              >
                Telegram
              </button>
              {' · '}
              <button
                type="button"
                className="text-indigo-600 hover:underline"
                onClick={() => go('connections')}
              >
                Google
              </button>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}

function StatusChip({ label, ok }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium ring-1 ${
        ok
          ? 'bg-emerald-50 text-emerald-800 ring-emerald-200'
          : 'bg-amber-50 text-amber-900 ring-amber-200'
      }`}
    >
      <span className={`size-1.5 rounded-full ${ok ? 'bg-emerald-500' : 'bg-amber-500'}`} />
      {label}
    </span>
  );
}
