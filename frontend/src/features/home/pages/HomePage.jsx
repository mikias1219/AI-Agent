import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  FolderKanban,
  Goal,
  ListTodo,
  Send,
  Sparkles,
  Zap,
} from 'lucide-react';
import { inferenceLabel } from '../../../shared/lib/runtime-status.js';
import AppMark from '../../../shared/components/ui/AppMark.jsx';

const openStatuses = new Set(['planned', 'in_progress', 'blocked']);

function greeting(name) {
  const hour = new Date().getHours();
  const part = hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
  return `${part}, ${name}`;
}

function hermesLabel(status) {
  if (!status) return { label: 'Hermes · Unknown', ok: false };
  if (status.active_runtime === 'hermes') return { label: 'Hermes Ready', ok: true };
  if (status.hermes_installed) return { label: 'Hermes Installed', ok: true };
  return { label: 'Hermes Unavailable', ok: false };
}

function ollamaLabel(status) {
  if (!status) return { label: 'Ollama · Unknown', ok: false };
  if (status.provider === 'fake' || status.active_runtime === 'fake')
    return { label: 'Ollama · N/A (test)', ok: false };
  if (status.ollama_reachable) return { label: 'Ollama Online', ok: true };
  return { label: 'Ollama Offline', ok: false };
}

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
  const openTasks = tasks.filter((t) => openStatuses.has(t.status));
  const taskPreview = openTasks.slice(0, 4);
  const pendingApprovals = approvals.filter((a) => a.actionable);
  const recentActivity = activity.slice(0, 4);
  const hermes = hermesLabel(status);
  const ollama = ollamaLabel(status);
  const telegramConfigured = !!status?.telegram?.configured;

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-5">
        <section className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-r from-[#3b1d8f] via-[#5b2dcf] to-[#2a6bdb] p-6 shadow-xl shadow-brand-600/20 sm:p-7">
          <div className="pointer-events-none absolute -right-8 -top-10 size-40 rounded-full bg-white/10 blur-2xl" />
          <div className="relative flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm text-white/70">AURA Overview</p>
              <h1 className="mt-2 max-w-xl text-2xl font-semibold tracking-tight text-white sm:text-3xl">
                {greeting(name)}
              </h1>
              <p className="mt-2 max-w-lg text-sm text-white/75">
                Let’s make today productive and meaningful — using only your real workspace data.
              </p>
            </div>
            <div className="glass max-w-xs border-white/20 bg-white/10 p-4 text-white">
              <p className="text-[10px] uppercase tracking-wider text-white/60">Focus</p>
              <p className="mt-1 text-sm font-medium">Dream bigger, achieve more</p>
              <p className="mt-2 text-[11px] text-white/65">
                Goals and calendar fill in when those modules ship.
              </p>
            </div>
          </div>
        </section>

        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatCard
            icon={ListTodo}
            label="Open tasks"
            value={String(openTasks.length)}
            hint="From your task list"
            tone="violet"
          />
          <StatCard
            icon={CalendarDays}
            label="Upcoming events"
            value="—"
            hint="Unavailable"
            tone="blue"
            unavailable
          />
          <StatCard
            icon={Goal}
            label="Goals progress"
            value="—"
            hint="Unavailable"
            tone="violet"
            unavailable
          />
          <StatCard
            icon={FolderKanban}
            label="Active projects"
            value="—"
            hint="Unavailable"
            tone="cyan"
            unavailable
          />
        </section>

        <section className="card relative overflow-hidden p-6">
          <div className="pointer-events-none absolute right-6 top-6 size-24 rounded-full bg-gradient-to-br from-brand-500/40 to-aura-cyan/30 blur-xl" />
          <div className="relative flex flex-wrap items-start gap-4">
            <div className="grid size-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-aura-cyan shadow-lg shadow-brand-600/40">
              <Sparkles className="text-white" size={26} />
            </div>
            <div className="min-w-0 flex-1">
              <h2 className="text-xl font-semibold">How can I help you today?</h2>
              <p className="mt-1 text-sm text-ink-400">
                Ask AURA — replies use your configured local runtime ({inferenceLabel(status)}).
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                {[
                  ['Plan my week', () => send('Help me plan my week.')],
                  [
                    'Review my open tasks',
                    () => send('Review my open tasks and suggest priorities.'),
                  ],
                  ['Open Telegram setup', () => go('telegram')],
                ].map(([label, fn]) => (
                  <button
                    key={label}
                    type="button"
                    onClick={fn}
                    className="rounded-full border border-white/10 bg-surface-800/80 px-3 py-1.5 text-[11px] text-ink-300 hover:border-brand-400/40 hover:text-ink-100"
                  >
                    {label}
                  </button>
                ))}
              </div>
              <form onSubmit={ask} className="mt-5 flex gap-2">
                <label htmlFor="home-request" className="sr-only">
                  Ask your agent
                </label>
                <input
                  id="home-request"
                  className="field flex-1"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Ask me anything…"
                />
                <button
                  className="primary px-4"
                  type="submit"
                  disabled={busy || !prompt.trim()}
                  aria-label="Ask my agent"
                >
                  <Send size={16} />
                </button>
              </form>
              <div className="mt-4 flex flex-wrap gap-3 text-[11px] text-ink-500">
                <span className={hermes.ok ? 'text-aura-emerald' : 'text-ink-500'}>
                  {hermes.label}
                </span>
                <span className={ollama.ok ? 'text-aura-emerald' : 'text-ink-500'}>
                  {ollama.label}
                </span>
                <span>Worker · Not connected yet</span>
                {pendingApprovals.length > 0 && (
                  <span className="text-aura-amber">
                    {pendingApprovals.length} pending approval
                    {pendingApprovals.length === 1 ? '' : 's'}
                  </span>
                )}
              </div>
              {status?.runtime_reason ? (
                <p className="mt-2 text-[11px] text-ink-500">{status.runtime_reason}</p>
              ) : null}
            </div>
          </div>
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <article className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">My Tasks</h2>
              <button onClick={() => go('tasks')} className="text-[11px] text-brand-400">
                View all
              </button>
            </div>
            {!taskPreview.length ? (
              <p className="py-8 text-center text-sm text-ink-500">No open tasks yet.</p>
            ) : (
              <ul className="space-y-3">
                {taskPreview.map((t) => (
                  <li
                    key={t.id}
                    className="flex items-center gap-3 rounded-xl border border-white/5 bg-surface-800/40 px-3 py-3"
                  >
                    <CheckCircle2 className="shrink-0 text-ink-500" size={16} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm">{t.title}</p>
                      <p className="text-[10px] uppercase tracking-wide text-ink-500">
                        {t.status.replaceAll('_', ' ')}
                      </p>
                    </div>
                    <PriorityChip status={t.status} />
                  </li>
                ))}
              </ul>
            )}
          </article>

          <article className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">Personal Goals</h2>
              <button onClick={() => go('growth')} className="text-[11px] text-brand-400">
                Open
              </button>
            </div>
            <div className="flex flex-col items-center justify-center py-6 text-center">
              <div className="grid size-24 place-items-center rounded-full border-4 border-white/10 border-t-brand-500">
                <span className="text-sm text-ink-500">N/A</span>
              </div>
              <p className="mt-4 text-sm font-medium">Goal tracking unavailable</p>
              <p className="mt-1 max-w-xs text-xs text-ink-500">
                Personal Growth and goals ship in a later phase. Nothing is simulated here.
              </p>
            </div>
          </article>
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <article className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">Knowledge Hub</h2>
              <button onClick={() => go('knowledge')} className="text-[11px] text-brand-400">
                Open
              </button>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {['Documents', 'Notes', 'Plans'].map((label) => (
                <div
                  key={label}
                  className="rounded-xl border border-dashed border-white/10 bg-surface-800/30 p-4 text-center"
                >
                  <BookOpen className="mx-auto text-ink-500" size={18} />
                  <p className="mt-2 text-[11px] text-ink-400">{label}</p>
                  <p className="mt-1 text-[9px] text-ink-500">Soon</p>
                </div>
              ))}
            </div>
          </article>

          <article className="card p-5">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-semibold">Integrations</h2>
              <button onClick={() => go('connections')} className="text-[11px] text-brand-400">
                Manage
              </button>
            </div>
            <ul className="space-y-3">
              <li className="flex items-center gap-3">
                <AppMark id="telegram" size="size-9" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm">Telegram</p>
                  <p className="text-[10px] text-ink-500">
                    {telegramConfigured ? 'Configured' : 'Setup needed'}
                  </p>
                </div>
                <button onClick={() => go('telegram')} className="text-[11px] text-brand-400">
                  Open
                </button>
              </li>
              <li className="flex items-center gap-3 opacity-70">
                <span className="grid size-9 place-items-center rounded-xl bg-surface-800 text-[10px] text-ink-500">
                  G
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm">Google</p>
                  <p className="text-[10px] text-ink-500">Not connected</p>
                </div>
              </li>
              <li className="flex items-center gap-3 opacity-70">
                <span className="grid size-9 place-items-center rounded-xl bg-surface-800 text-[10px] text-ink-500">
                  @
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm">Email</p>
                  <p className="text-[10px] text-ink-500">Unavailable</p>
                </div>
              </li>
            </ul>
          </article>
        </section>
      </div>

      <aside className="space-y-5">
        <article className="card p-5">
          <h2 className="mb-4 font-semibold">AI System Status</h2>
          <ul className="space-y-3 text-sm">
            <StatusRow label="Hermes Agent" value={hermes.label} ok={hermes.ok} />
            <StatusRow label="Ollama (Local)" value={ollama.label} ok={ollama.ok} />
            <StatusRow label="Local Worker" value="Not connected yet" ok={false} />
            <StatusRow
              label="Runtime"
              value={status?.active_runtime || 'unknown'}
              ok={status?.active_runtime === 'hermes' || status?.active_runtime === 'ollama_agent'}
            />
          </ul>
          <div className="mt-4 h-10 overflow-hidden rounded-xl border border-white/5 bg-surface-800/50">
            <div className="flex h-full items-end gap-0.5 px-2 py-1.5">
              {Array.from({ length: 24 }).map((_, i) => (
                <span
                  key={i}
                  className="flex-1 rounded-sm bg-brand-500/30"
                  style={{ height: `${20 + ((i * 37) % 70)}%` }}
                />
              ))}
            </div>
          </div>
        </article>

        <article className="card p-5">
          <h2 className="mb-4 font-semibold">Upcoming Events</h2>
          <p className="rounded-xl border border-dashed border-white/10 px-3 py-8 text-center text-xs text-ink-500">
            Calendar unavailable — coming in a later phase.
          </p>
        </article>

        <article className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold">Recent Activity</h2>
            <button onClick={() => go('activity')} className="text-[11px] text-brand-400">
              All
            </button>
          </div>
          {!recentActivity.length ? (
            <p className="py-6 text-center text-xs text-ink-500">No activity yet.</p>
          ) : (
            <ul className="space-y-3">
              {recentActivity.map((e) => (
                <li key={e.id} className="border-b border-white/5 pb-3 last:border-0">
                  <p className="text-xs text-ink-100">
                    {e.event.replaceAll('_', ' ').replaceAll('.', ' · ')}
                  </p>
                  <p className="mt-1 text-[10px] text-ink-500">
                    {new Date(e.occurred_at).toLocaleString()}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="overflow-hidden rounded-2xl border border-brand-500/30 bg-gradient-to-br from-brand-600/40 to-surface-900 p-5">
          <div className="mb-3 inline-flex rounded-xl bg-white/10 p-2 text-brand-400">
            <Zap size={18} />
          </div>
          <h2 className="text-sm font-semibold">Your Personal AI Assistant</h2>
          <p className="mt-2 text-xs leading-5 text-ink-300">
            Continue in My Agent with the same tools, approvals, and conversation history.
          </p>
          <button className="primary mt-4 w-full" onClick={() => go('agent')}>
            Explore My Agent
            <ArrowRight size={14} />
          </button>
        </article>
      </aside>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, hint, unavailable }) {
  return (
    <div className="card p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="rounded-lg bg-brand-50 p-2 text-brand-400">
          <Icon size={16} />
        </span>
        {unavailable && <span className="text-[9px] uppercase text-ink-500">Soon</span>}
      </div>
      <p className="text-[11px] text-ink-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-[10px] text-ink-500">{hint}</p>
    </div>
  );
}

function PriorityChip({ status }) {
  const tone =
    status === 'in_progress'
      ? 'bg-aura-rose/15 text-aura-rose'
      : status === 'blocked'
        ? 'bg-aura-amber/15 text-aura-amber'
        : 'bg-brand-50 text-brand-400';
  return (
    <span
      className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase ${tone}`}
    >
      {status === 'in_progress' ? 'High' : status === 'blocked' ? 'Blocked' : 'Medium'}
    </span>
  );
}

function StatusRow({ label, value, ok }) {
  return (
    <li className="flex items-center justify-between gap-3">
      <span className="text-ink-400">{label}</span>
      <span className={`text-xs ${ok ? 'text-aura-emerald' : 'text-aura-amber'}`}>{value}</span>
    </li>
  );
}
