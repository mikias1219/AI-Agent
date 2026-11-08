import { ArrowRight, CalendarDays, ShieldCheck, WandSparkles } from 'lucide-react';
import EmptyState from '../../../shared/components/ui/EmptyState.jsx';
import StatusPill from '../../../shared/components/ui/StatusPill.jsx';
import { inferenceLabel, ollamaReachableLabel } from '../../../shared/lib/runtime-status.js';

const openStatuses = new Set(['planned', 'in_progress', 'blocked']);

export default function HomePage({
  name,
  prompt,
  setPrompt,
  ask,
  busy,
  send,
  go,
  status,
  tasks,
  approvals = [],
  activity = [],
}) {
  const openTasks = tasks.filter((t) => openStatuses.has(t.status)).slice(0, 5);
  const pendingApprovals = approvals.filter((a) => a.actionable);
  const recentActivity = activity.slice(0, 5);
  const providerLabel = inferenceLabel(status);

  return (
    <>
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow mb-2">Overview</p>
          <h1 className="text-3xl font-semibold tracking-tight text-ink-100 sm:text-4xl">
            Hey {name}, let’s make today easier<span className="text-brand-400">.</span>
          </h1>
          <p className="mt-3 max-w-xl text-sm text-ink-400">
            Your personal AI operating system. Live data only — nothing simulated.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <StatusPill
            label={providerLabel}
            tone={
              status?.active_runtime === 'fake' || status?.provider === 'fake'
                ? 'warning'
                : 'accent'
            }
          />
          <StatusPill
            label={ollamaReachableLabel(status)}
            tone={status?.ollama_reachable ? 'success' : 'warning'}
          />
          <StatusPill label="Worker · Not connected yet" tone="warning" />
        </div>
      </div>
      {status?.runtime_reason ? (
        <p className="mb-6 text-xs text-ink-500">{status.runtime_reason}</p>
      ) : null}

      <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-brand-50 via-surface-900 to-surface-950 p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-16 -top-16 size-56 rounded-full border border-brand-200/40" />
        <div className="relative">
          <div className="mb-5 flex items-center gap-2 text-sm font-medium text-brand-400">
            <WandSparkles size={18} />
            Ask AURA
          </div>
          <h2 className="mb-2 text-2xl font-semibold tracking-tight text-ink-100">
            What should we work on?
          </h2>
          <p className="mb-6 text-sm text-ink-400">
            A short request opens My Agent with your real conversation history.
          </p>
          <form onSubmit={ask} className="rounded-2xl border border-white/10 bg-surface-950/80 p-3">
            <label htmlFor="home-request" className="sr-only">
              Ask your agent
            </label>
            <textarea
              id="home-request"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="w-full resize-none border-0 bg-transparent px-3 py-2 text-sm leading-7 text-ink-100 focus:outline-none focus:ring-0"
              placeholder="Ask a question, plan a task, or tell me what you need…"
              rows={2}
            />
            <div className="flex flex-wrap items-center justify-between gap-3 px-2">
              <span className="flex items-center gap-1.5 text-[10px] text-ink-500">
                <ShieldCheck size={13} />
                You review consequential actions.
              </span>
              <button className="primary py-2.5" type="submit" disabled={busy || !prompt.trim()}>
                Ask my agent
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
        </div>
      </section>

      <div className="mt-8 grid gap-5 xl:grid-cols-2">
        <section className="card p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="font-semibold text-ink-100">Priority tasks</h2>
            <button onClick={() => go('tasks')} className="text-[11px] font-medium text-brand-400">
              View all
            </button>
          </div>
          {!openTasks.length ? (
            <EmptyState title="No open tasks">
              Create a task from Tasks & Goals when you are ready.
            </EmptyState>
          ) : (
            <ul className="space-y-3">
              {openTasks.map((t) => (
                <li
                  key={t.id}
                  className="flex items-center justify-between gap-3 border-b border-white/10 py-3 last:border-0"
                >
                  <span className="text-sm text-ink-100">{t.title}</span>
                  <span className="text-[10px] uppercase tracking-wide text-ink-500">
                    {t.status.replaceAll('_', ' ')}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-4 text-xs text-ink-500">
            {pendingApprovals.length} pending approval
            {pendingApprovals.length === 1 ? '' : 's'}.
          </p>
        </section>

        <section className="card p-6">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="font-semibold text-ink-100">Recent activity</h2>
            <button
              onClick={() => go('activity')}
              className="text-[11px] font-medium text-brand-400"
            >
              Activity & Logs
            </button>
          </div>
          {!recentActivity.length ? (
            <EmptyState title="No activity yet">
              Chat, tasks, and Telegram actions will appear here.
            </EmptyState>
          ) : (
            <ul className="space-y-3">
              {recentActivity.map((e) => (
                <li key={e.id} className="border-b border-white/10 py-3 last:border-0">
                  <p className="text-sm text-ink-100">
                    {e.event.replaceAll('_', ' ').replaceAll('.', ' · ')}
                  </p>
                  <p className="mt-1 text-[10px] text-ink-500">
                    {new Date(e.occurred_at).toLocaleString()}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="mt-5 grid gap-5 md:grid-cols-2">
        <section className="card p-6">
          <div className="mb-3 flex items-center gap-2 text-ink-300">
            <CalendarDays size={16} />
            <h2 className="font-semibold text-ink-100">Upcoming events</h2>
          </div>
          <EmptyState title="Unavailable">
            Calendar arrives in a later phase. No events are invented here.
          </EmptyState>
        </section>
        <section className="card p-6">
          <h2 className="mb-3 font-semibold text-ink-100">Active projects & goals</h2>
          <EmptyState title="Unavailable">
            Goals and projects are not modeled yet. Open tasks above are the current source of
            truth.
          </EmptyState>
          <button
            onClick={() => send('Help me plan my day.')}
            className="secondary mt-4 w-full"
            disabled={busy}
          >
            Plan my day with My Agent
          </button>
        </section>
      </div>
    </>
  );
}
