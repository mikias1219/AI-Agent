import { useState } from 'react';
import { CHANNELS, WORKFLOW_STATUSES } from '../channels.js';
import { channelPath } from '../routes.js';
import { inferenceLabel, ollamaReachableLabel } from '../../../shared/lib/runtime-status.js';

export default function HubDashboardPage({ hub, status, approvals, go, name, onAskAgent }) {
  const [ask, setAsk] = useState('');
  const live = CHANNELS.filter((c) => c.live);
  const scaffold = CHANNELS.filter((c) => !c.live);
  const skills = hub.skills || [];
  const ideas = hub.ideas || [];
  const pending = (approvals || []).filter((a) => a.actionable);
  const overdue = ideas.filter((i) => i.stage === 'now' && i.effort > 4);
  const telegramOk = !!status?.telegram?.configured;
  const googleConnected = !!hub.google?.connected;

  const attention = [];
  pending.slice(0, 6).forEach((a) =>
    attention.push({
      id: a.id,
      tag: 'Approval',
      tone: 'bg-indigo-100 text-indigo-700',
      path: 'approvals',
      text: `${a.tool_name} needs a decision`,
    }),
  );
  if (!telegramOk) {
    attention.push({
      id: 'tg-config',
      tag: 'Connect',
      tone: 'bg-sky-100 text-sky-700',
      path: channelPath('telegram'),
      text: 'Configure Telegram bot token to go live',
    });
  }
  if (!googleConnected) {
    attention.push({
      id: 'g-config',
      tag: 'Connect',
      tone: 'bg-amber-100 text-amber-800',
      path: 'connections',
      text: 'Connect Google for Gmail, Calendar, and Drive',
    });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">
            {name ? `Welcome back, ${name.split(' ')[0]}` : 'Dashboard'}
          </h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Channel health, skill readiness, and approvals — no invented activity.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200">
            {inferenceLabel(status)}
          </span>
          <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 ring-1 ring-slate-200">
            {ollamaReachableLabel(status)}
          </span>
        </div>
      </header>

      <section className="overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600 to-indigo-800 p-5 text-white shadow-lg shadow-indigo-600/20">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-indigo-100">Ask your agent</h2>
            <p className="mt-1 text-sm text-indigo-100/90">
              Opens My Agent with your message. Sends and writes still need approval.
            </p>
          </div>
          <button
            type="button"
            onClick={() => go('agent')}
            className="rounded-lg bg-white/15 px-3 py-1.5 text-xs font-semibold text-white ring-1 ring-white/30 hover:bg-white/25"
          >
            Open full agent
          </button>
        </div>
        <form
          className="mt-4 flex flex-col gap-2 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            if (!ask.trim()) return;
            onAskAgent?.(ask.trim());
            setAsk('');
          }}
        >
          <input
            value={ask}
            onChange={(e) => setAsk(e.target.value)}
            placeholder="e.g. Draft a Telegram reply I can approve…"
            className="min-w-0 flex-1 rounded-xl border-0 bg-white/95 px-4 py-3 text-sm text-slate-900 outline-none placeholder:text-slate-400 focus:ring-4 focus:ring-white/30"
          />
          <button
            type="submit"
            disabled={!ask.trim()}
            className="rounded-xl bg-white px-4 py-3 text-sm font-semibold text-indigo-700 disabled:opacity-50"
          >
            Ask agent
          </button>
        </form>
      </section>

      <section className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6" aria-label="Totals">
        <Tile label="Skills" value={skills.length} />
        <Tile
          label="Live or in build"
          value={skills.filter((s) => s.status === 'live' || s.status === 'building').length}
        />
        <Tile label="Approvals waiting" value={pending.length} />
        <Tile label="Live channels" value={live.length} />
        <Tile label="Scaffolded" value={scaffold.length} />
        <Tile label="Roadmap items" value={ideas.length} />
      </section>

      {attention.length > 0 && (
        <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
          <h2 className="text-sm font-semibold text-slate-900">Needs attention</h2>
          <ul className="mt-2 divide-y divide-slate-100 text-sm">
            {attention.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => go(item.path)}
                  className="flex w-full items-center gap-3 py-2 text-left hover:bg-slate-50"
                >
                  <span
                    className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${item.tone}`}
                  >
                    {item.tag}
                  </span>
                  <span className="text-slate-700">{item.text}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="grid gap-4 lg:grid-cols-2" aria-label="Live channels">
        {live.map((ch) => (
          <ChannelCard
            key={ch.id}
            channel={ch}
            skills={skills.filter((s) => s.channelId === ch.id)}
            ideas={ideas.filter((i) => i.channelId === ch.id)}
            connected={
              ch.id === 'telegram' ? telegramOk : ch.group === 'google' ? googleConnected : false
            }
            go={go}
          />
        ))}
      </section>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Social & messaging scaffolds</h2>
        <p className="mt-1 text-xs text-slate-500">
          Shown in the sidebar for planning. Not connected in v1 — no fake metrics.
        </p>
        <table className="mt-3 w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500">
              <th className="py-1.5 font-medium">Channel</th>
              <th className="font-medium">Group</th>
              <th className="font-medium">Planned skills</th>
              <th className="font-medium">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {scaffold.map((ch) => (
              <tr key={ch.id}>
                <td className="py-2">
                  <button
                    type="button"
                    className="font-medium text-slate-900 hover:text-indigo-700"
                    onClick={() => go(channelPath(ch.id))}
                  >
                    {ch.name}
                  </button>
                </td>
                <td className="capitalize text-slate-600">{ch.group}</td>
                <td className="text-slate-600">{ch.plannedSkills?.length || 0}</td>
                <td className="text-slate-500">Coming later</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {overdue.length > 0 && (
        <p className="text-xs text-slate-400">{overdue.length} heavy Now items on the roadmap.</p>
      )}
    </div>
  );
}

function Tile({ label, value }) {
  return (
    <div className="rounded-xl bg-white px-4 py-3 ring-1 ring-slate-200">
      <div className="text-2xl font-semibold tabular-nums text-slate-900">{value}</div>
      <div className="text-xs text-slate-500">{label}</div>
    </div>
  );
}

function ChannelCard({ channel, skills, ideas, connected, go }) {
  return (
    <button
      type="button"
      onClick={() => go(channelPath(channel.id))}
      className="rounded-2xl bg-white p-5 text-left ring-1 ring-slate-200 hover:ring-indigo-300"
    >
      <div className="flex items-center gap-3">
        <span className={`size-3 rounded-full ${channel.color}`} />
        <div className="min-w-0 flex-1">
          <div className="font-semibold text-slate-900">{channel.fullName || channel.name}</div>
          <div className="text-xs text-slate-500">
            {connected ? 'Connected path available' : 'Not connected yet'}
          </div>
        </div>
      </div>
      <p className="mt-3 line-clamp-2 text-sm text-slate-600">{channel.description}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {WORKFLOW_STATUSES.map((st) => {
          const n = skills.filter((s) => s.status === st.id).length;
          if (!n) return null;
          return (
            <span
              key={st.id}
              className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${st.style}`}
            >
              {n} {st.label}
            </span>
          );
        })}
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
          {ideas.length} roadmap
        </span>
      </div>
    </button>
  );
}
