import {
  Activity,
  ArrowRight,
  Bot,
  CalendarDays,
  CheckCircle2,
  Circle,
  Clock3,
  Database,
  Inbox,
  LockKeyhole,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Target,
  Terminal,
  WandSparkles,
  Zap,
} from 'lucide-react';
import EmptyState from '../../../shared/components/ui/EmptyState.jsx';
import StatusPill from '../../../shared/components/ui/StatusPill.jsx';
import { inferenceLabel, ollamaReachableLabel } from '../../../shared/lib/runtime-status.js';

const OPEN_STATUSES = new Set(['planned', 'in_progress', 'blocked']);

function formatTime(value) {
  if (!value) return 'Time unavailable';
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Time unavailable'
    : date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
}

function StatCard({ icon: Icon, label, value, detail, tone = 'blue' }) {
  const tones = {
    blue: 'bg-sky-500/10 text-sky-300 ring-sky-400/20',
    violet: 'bg-violet-500/10 text-violet-300 ring-violet-400/20',
    teal: 'bg-teal-500/10 text-teal-300 ring-teal-400/20',
    amber: 'bg-amber-500/10 text-amber-300 ring-amber-400/20',
  };

  return (
    <article className="aura-panel flex min-w-0 items-center gap-4 p-4 sm:p-5">
      <div className={`grid size-11 shrink-0 place-items-center rounded-2xl ring-1 ${tones[tone]}`}>
        <Icon size={20} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-ink-400">{label}</p>
        <p className="mt-1 text-2xl font-semibold tracking-tight text-ink-100">{value}</p>
        <p className="mt-1 truncate text-[11px] text-ink-500">{detail}</p>
      </div>
    </article>
  );
}

function SectionHeading({ icon: Icon, title, action, onAction }) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div className="flex min-w-0 items-center gap-2.5">
        <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-brand-100 text-brand-400">
          <Icon size={16} />
        </span>
        <h2 className="truncate text-sm font-semibold text-ink-100 sm:text-base">{title}</h2>
      </div>
      {action && (
        <button
          type="button"
          onClick={onAction}
          className="inline-flex shrink-0 items-center gap-1 text-xs font-medium text-brand-400 transition hover:text-white"
        >
          {action} <ArrowRight size={13} />
        </button>
      )}
    </div>
  );
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
  tasks = [],
  approvals = [],
  activity = [],
}) {
  const openTasks = tasks.filter((task) => OPEN_STATUSES.has(task.status));
  const pendingApprovals = approvals.filter((item) => item.actionable);
  const recentActivity = activity.slice(0, 5);
  const providerLabel = inferenceLabel(status);
  const ollamaLabel = ollamaReachableLabel(status);
  const localReady = !!status?.ollama_reachable;
  const runtimeReady =
    status?.active_runtime !== 'fake' && status?.provider !== 'fake' && !!status?.active_runtime;

  return (
    <main className="aura-overview space-y-6">
      {/* Welcome banner */}
      <section className="aura-hero relative overflow-hidden rounded-3xl border border-white/10 px-5 py-6 sm:px-7 sm:py-8">
        <div className="aura-hero-orb aura-hero-orb-one" />
        <div className="aura-hero-orb aura-hero-orb-two" />
        <div className="relative z-10 flex flex-col justify-between gap-5 lg:flex-row lg:items-end">
          <div>
            <p className="eyebrow mb-2">Your personal AI operating system</p>
            <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl lg:text-4xl">
              Good day, {name}
              <span className="text-brand-400">.</span>
            </h1>
            <p className="mt-2 max-w-xl text-sm leading-6 text-slate-300">
              A clear view of your work, priorities, and personal AI workspace.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <StatusPill label={providerLabel} tone={runtimeReady ? 'success' : 'warning'} />
            <StatusPill label={ollamaLabel} tone={localReady ? 'success' : 'warning'} />
          </div>
        </div>
      </section>

      {/* Real-data summary cards. No fabricated calendar or goal metrics. */}
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          icon={CheckCircle2}
          label="Open tasks"
          value={openTasks.length}
          detail={`${tasks.length} total tasks in your workspace`}
          tone="blue"
        />
        <StatCard
          icon={ShieldCheck}
          label="Pending approvals"
          value={pendingApprovals.length}
          detail={pendingApprovals.length ? 'Your review is needed' : 'Nothing waiting for review'}
          tone="violet"
        />
        <StatCard
          icon={Activity}
          label="Recent activity"
          value={activity.length}
          detail="Recorded workspace events"
          tone="teal"
        />
        <StatCard
          icon={Zap}
          label="Local AI"
          value={localReady ? 'Ready' : 'Offline'}
          detail={status?.model || 'Ollama status from backend'}
          tone="amber"
        />
      </section>

      {/* Main workspace columns */}
      <section className="grid items-start gap-5 2xl:grid-cols-[1.12fr_0.88fr_280px]">
        {/* Agent panel */}
        <article className="aura-panel aura-agent-panel min-w-0 p-5 sm:p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <SectionHeading icon={Bot} title="My Agent" />
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-medium text-emerald-300">
              <span className="size-1.5 rounded-full bg-emerald-400" />
              {busy ? 'Working' : 'Available'}
            </span>
          </div>

          <div className="aura-agent-welcome mb-5 flex items-start gap-3 rounded-2xl border border-white/5 p-4">
            <div className="grid size-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 shadow-lg shadow-violet-950/50">
              <Sparkles size={21} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-white">How can I help you today?</p>
              <p className="mt-1 text-xs leading-5 text-slate-400">
                Ask AURA to organize your work, think through a problem, or help you take the next
                step.
              </p>
            </div>
          </div>

          <div className="mb-4 flex flex-wrap gap-2">
            {[
              ['Plan my day', 'Help me plan my day using my open tasks.'],
              ['Review priorities', 'Review my open tasks and help me prioritize them.'],
              ['Summarize activity', 'Summarize my recent workspace activity.'],
            ].map(([label, message]) => (
              <button
                key={label}
                type="button"
                onClick={() => send(message)}
                disabled={busy}
                className="aura-suggestion"
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={ask} className="aura-prompt-box">
            <label htmlFor="aura-home-prompt" className="sr-only">
              Message your agent
            </label>
            <textarea
              id="aura-home-prompt"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              rows={2}
              placeholder="Ask me anything..."
              className="w-full resize-none border-0 bg-transparent px-3 py-2 text-sm leading-6 text-white placeholder:text-slate-500 focus:outline-none focus:ring-0"
            />
            <div className="flex items-center justify-between gap-3 px-2 pb-1">
              <span className="inline-flex items-center gap-1.5 text-[10px] text-slate-500">
                <LockKeyhole size={12} />
                Consequential actions require your approval.
              </span>
              <button
                type="submit"
                disabled={busy || !prompt.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-xs font-semibold text-white transition hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {busy ? 'Working' : 'Ask AURA'}
                <ArrowRight size={14} />
              </button>
            </div>
          </form>
          <button
            type="button"
            onClick={() => go('agent')}
            className="mt-4 inline-flex items-center gap-2 text-xs font-medium text-brand-400 hover:text-white"
          >
            Open full agent workspace <ArrowRight size={13} />
          </button>
        </article>

        {/* Tasks */}
        <article className="aura-panel min-w-0 p-5 sm:p-6">
          <SectionHeading
            icon={CheckCircle2}
            title="My Tasks"
            action="View all"
            onAction={() => go('tasks')}
          />
          {openTasks.length === 0 ? (
            <EmptyState title="No open tasks">
              Your active tasks will appear here when they are created.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-white/[0.07]">
              {openTasks.slice(0, 6).map((task) => (
                <li key={task.id} className="flex items-start gap-3 py-3 first:pt-1">
                  <Circle size={17} className="mt-0.5 shrink-0 text-slate-500" />
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm text-slate-200">{task.title}</p>
                    <p className="mt-1 text-[10px] capitalize text-slate-500">
                      {String(task.status || 'open').replaceAll('_', ' ')}
                    </p>
                  </div>
                  {task.priority && (
                    <span className="shrink-0 rounded-full bg-white/5 px-2 py-1 text-[10px] capitalize text-slate-400">
                      {task.priority}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
          <button type="button" onClick={() => go('tasks')} className="secondary mt-4 w-full">
            Manage tasks
          </button>
        </article>

        {/* System status */}
        <aside className="grid gap-4 sm:grid-cols-2 2xl:grid-cols-1">
          <article className="aura-panel p-5">
            <SectionHeading icon={Terminal} title="System status" />
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="grid size-9 place-items-center rounded-xl bg-emerald-500/10 text-emerald-300">
                  <Bot size={17} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-200">AI runtime</p>
                  <p className="truncate text-[11px] text-slate-400">{providerLabel}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="grid size-9 place-items-center rounded-xl bg-violet-500/10 text-violet-300">
                  <Zap size={17} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-200">Ollama</p>
                  <p className="truncate text-[11px] text-slate-400">{ollamaLabel}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="grid size-9 place-items-center rounded-xl bg-sky-500/10 text-sky-300">
                  <Database size={17} />
                </span>
                <div className="min-w-0">
                  <p className="text-xs font-medium text-slate-200">Workspace API</p>
                  <p className="truncate text-[11px] text-slate-400">
                    {status ? 'Status received from backend' : 'Status unavailable'}
                  </p>
                </div>
              </div>
            </div>
            {status?.runtime_reason && (
              <p className="mt-4 border-t border-white/[0.07] pt-3 text-[10px] leading-5 text-slate-500">
                {status.runtime_reason}
              </p>
            )}
          </article>

          <article className="aura-privacy-panel rounded-2xl border border-cyan-400/20 p-5">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-xl bg-cyan-400/10 text-cyan-300">
                <ShieldCheck size={20} />
              </span>
              <div>
                <p className="text-sm font-semibold text-white">Private by default</p>
                <p className="mt-1 text-[11px] text-slate-400">You stay in control of actions.</p>
              </div>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-400">
              Review approval requests before AURA performs consequential actions.
            </p>
            <button
              type="button"
              onClick={() => go('settings')}
              className="mt-3 text-xs font-medium text-cyan-300 hover:text-white"
            >
              Privacy settings <ArrowRight size={12} className="ml-1 inline" />
            </button>
          </article>
        </aside>
      </section>

      {/* Lower dashboard: schedule is deliberately honest until calendar data exists. */}
      <section className="grid gap-5 xl:grid-cols-[0.85fr_1.15fr]">
        <article className="aura-panel p-5 sm:p-6">
          <SectionHeading
            icon={CalendarDays}
            title="Upcoming schedule"
            action="Open calendar"
            onAction={() => go('calendar')}
          />
          <div className="flex min-h-36 flex-col items-center justify-center rounded-2xl border border-dashed border-white/10 px-5 py-6 text-center">
            <Clock3 size={22} className="text-slate-500" />
            <p className="mt-3 text-sm font-medium text-slate-300">
              Calendar data is not connected yet
            </p>
            <p className="mt-1 max-w-sm text-xs leading-5 text-slate-500">
              Once calendar integration is implemented, your real events will appear here.
            </p>
            <button
              type="button"
              onClick={() => go('calendar')}
              className="mt-3 text-xs font-medium text-brand-400 hover:text-white"
            >
              Go to calendar
            </button>
          </div>
        </article>

        <article className="aura-panel p-5 sm:p-6">
          <SectionHeading
            icon={Activity}
            title="Recent activity"
            action="View logs"
            onAction={() => go('activity')}
          />
          {!recentActivity.length ? (
            <EmptyState title="No recent activity">
              Your agent, tasks, and connected services will add events here.
            </EmptyState>
          ) : (
            <ul className="divide-y divide-white/[0.07]">
              {recentActivity.map((event) => (
                <li key={event.id} className="flex items-start gap-3 py-3 first:pt-1">
                  <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-brand-100 text-brand-400">
                    <Activity size={15} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="break-words text-sm text-slate-200">
                      {String(event.event || 'Workspace event')
                        .replaceAll('_', ' ')
                        .replaceAll('.', ' · ')}
                    </p>
                    <p className="mt-1 text-[10px] text-slate-500">
                      {formatTime(event.occurred_at)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      {pendingApprovals.length > 0 && (
        <button
          type="button"
          onClick={() => go('approvals')}
          className="flex w-full items-center justify-between gap-3 rounded-2xl border border-amber-400/20 bg-amber-400/[0.06] p-4 text-left transition hover:bg-amber-400/10"
        >
          <span className="flex items-center gap-3">
            <span className="grid size-9 place-items-center rounded-xl bg-amber-400/10 text-amber-300">
              <ShieldCheck size={17} />
            </span>
            <span>
              <span className="block text-sm font-semibold text-amber-100">
                {pendingApprovals.length} approval{pendingApprovals.length === 1 ? '' : 's'} need
                your attention
              </span>
              <span className="mt-1 block text-xs text-amber-200/60">
                Review them before any consequential action is performed.
              </span>
            </span>
          </span>
          <ArrowRight size={17} className="shrink-0 text-amber-300" />
        </button>
      )}
    </main>
  );
}
