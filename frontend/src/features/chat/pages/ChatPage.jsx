import { Send, Plus, RefreshCw } from 'lucide-react';
import PageHeading from '../../../shared/components/ui/PageHeading.jsx';

export default function ChatPage({
  chat,
  prompt,
  setPrompt,
  ask,
  busy,
  conversations,
  loadConversation,
  newConversation,
  sessionId,
  approvals,
  decide,
}) {
  return (
    <>
      <PageHeading
        eyebrow="One agent, wherever you ask"
        title="Let’s work on it together."
        action={
          <button className="secondary" disabled={busy} onClick={newConversation}>
            <Plus size={15} />
            New conversation
          </button>
        }
      >
        Your dashboard and Telegram use the same agent service. Choose a previous conversation to
        continue it here.
      </PageHeading>
      <div className="grid items-start gap-5 xl:grid-cols-[230px_1fr]">
        <aside className="card max-h-96 overflow-y-auto p-4">
          <h2 className="mb-3 text-sm font-semibold">Conversations</h2>
          {!conversations.length && (
            <p className="text-xs leading-6 text-slate-500">
              Your first conversation will appear here.
            </p>
          )}
          {conversations.map((c) => (
            <button
              disabled={busy}
              key={c.id}
              onClick={() => loadConversation(c.id)}
              className={`mb-2 w-full rounded-xl p-3 text-left text-xs ${sessionId === c.id ? 'bg-brand-50 text-brand-700' : 'hover:bg-slate-50 text-slate-600'}`}
            >
              <span className="block font-medium">
                {c.user_id.startsWith('telegram:')
                  ? 'Telegram'
                  : c.user_id === 'dashboard'
                    ? 'Dashboard'
                    : c.user_id}{' '}
                · {c.id.slice(0, 6)}
              </span>
              <span className="mt-1 block text-[10px] text-slate-400">
                {new Date(c.created_at).toLocaleString()}
              </span>
            </button>
          ))}
        </aside>
        <section className="card overflow-hidden">
          <div
            className="max-h-[60vh] min-h-80 space-y-4 overflow-y-auto p-5 sm:p-8"
            aria-live="polite"
          >
            {!chat.length && (
              <div className="py-16 text-center">
                <h2 className="font-semibold">What would make today easier?</h2>
                <p className="mt-3 text-sm text-slate-500">
                  Ask a question, explain a task, or plan your next step.
                </p>
              </div>
            )}
            {chat
              .filter((m) => m.content)
              .map((m, i) => (
                <div
                  key={i}
                  className={`max-w-xl whitespace-pre-wrap break-words rounded-2xl p-4 text-sm leading-7 ${m.role === 'user' ? 'ml-auto bg-brand-600 text-white' : 'bg-slate-50 text-slate-600'}`}
                >
                  {m.content}
                  {m.incomplete && (
                    <p className="mt-2 text-xs font-medium text-rose-600">
                      Incomplete reply — the model connection failed.
                    </p>
                  )}
                </div>
              ))}
            {busy && (
              <p role="status" className="flex items-center gap-2 text-xs text-brand-600">
                <RefreshCw className="animate-spin" size={14} />
                Your agent is working…
              </p>
            )}
          </div>
          {approvals
            .filter((a) => a.actionable)
            .map((a) => (
              <div
                key={a.id}
                className="mx-5 mb-4 rounded-xl border border-amber-200 bg-amber-50 p-4"
              >
                <p className="text-sm font-semibold">Approval needed: {a.tool_name}</p>
                <pre className="my-3 overflow-auto whitespace-pre-wrap text-xs">
                  {JSON.stringify(a.arguments, null, 2)}
                </pre>
                <div className="flex gap-2">
                  <button className="primary" onClick={() => decide(a.id, true)}>
                    Approve
                  </button>
                  <button className="secondary" onClick={() => decide(a.id, false)}>
                    Deny
                  </button>
                </div>
              </div>
            ))}
          <form onSubmit={ask} className="flex gap-3 border-t border-slate-100 p-4">
            <label className="sr-only" htmlFor="chat-input">
              Message your agent
            </label>
            <textarea
              id="chat-input"
              className="field min-w-0 resize-y"
              rows={2}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              maxLength={10000}
              placeholder="What’s on your mind?"
              required
              disabled={busy}
            />
            <button
              className="primary self-end"
              disabled={busy || !prompt.trim()}
              aria-label="Send message"
            >
              <Send size={17} />
            </button>
          </form>
        </section>
      </div>
    </>
  );
}
