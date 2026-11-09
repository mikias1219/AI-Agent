import { useState } from 'react';
import { CHANNELS, STAGES, riceScore } from '../channels.js';
import { channelPath } from '../routes.js';

export default function HubRoadmapPage({ hub, channelId = null, go, notify }) {
  const [title, setTitle] = useState('');
  const [stage, setStage] = useState('now');
  const ideas = (hub.ideas || []).filter((i) => (channelId ? i.channelId === channelId : true));

  async function addIdea(e) {
    e.preventDefault();
    if (!title.trim()) return;
    const idea = {
      id: `idea-${Date.now()}`,
      title: title.trim(),
      description: '',
      channelId: channelId || 'telegram',
      stage,
      owner: 'You',
      reach: 1,
      impact: 1,
      confidence: 80,
      effort: 1,
      createdAt: new Date().toISOString().slice(0, 10),
    };
    try {
      await hub.updateIdeas([...(hub.ideas || []), idea]);
      setTitle('');
      notify?.('Roadmap item added.');
    } catch (err) {
      notify?.(err.message);
    }
  }

  async function setIdeaStage(id, nextStage) {
    try {
      await hub.updateIdeas(
        (hub.ideas || []).map((i) => (i.id === id ? { ...i, stage: nextStage } : i)),
      );
    } catch (err) {
      notify?.(err.message);
    }
  }

  return (
    <div className="space-y-5">
      {!channelId && (
        <header>
          <h1 className="text-xl font-semibold text-slate-900">Ideas & roadmap</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Now / Next / Later for personal automations across channels.
          </p>
        </header>
      )}

      <form onSubmit={addIdea} className="flex flex-wrap items-end gap-2">
        <label className="min-w-[14rem] flex-1 text-sm">
          <span className="mb-1 block text-xs font-medium text-slate-500">Title</span>
          <input
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="New automation idea…"
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block text-xs font-medium text-slate-500">Stage</span>
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            value={stage}
            onChange={(e) => setStage(e.target.value)}
          >
            {STAGES.map((s) => (
              <option key={s.id} value={s.id}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        >
          Add
        </button>
      </form>

      <div className="grid gap-4 lg:grid-cols-5">
        {STAGES.map((s) => {
          const column = ideas.filter((i) => i.stage === s.id);
          return (
            <section key={s.id} className="rounded-2xl bg-white p-3 ring-1 ring-slate-200">
              <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                {s.label} <span className="tabular-nums text-slate-400">({column.length})</span>
              </h2>
              <ul className="space-y-2">
                {column.map((idea) => {
                  const ch = CHANNELS.find((c) => c.id === idea.channelId);
                  return (
                    <li key={idea.id} className="rounded-xl bg-slate-50 p-3 ring-1 ring-slate-100">
                      <button
                        type="button"
                        className="text-left text-sm font-medium text-slate-900 hover:text-indigo-700"
                        onClick={() => ch && go(channelPath(ch.id, 'roadmap'))}
                      >
                        {idea.title}
                      </button>
                      <div className="mt-1 flex items-center justify-between gap-2 text-[11px] text-slate-500">
                        <span>{ch?.name || idea.channelId}</span>
                        <span>RICE {riceScore(idea)}</span>
                      </div>
                      <select
                        className="mt-2 w-full rounded border border-slate-200 bg-white px-2 py-1 text-xs"
                        value={idea.stage}
                        onChange={(e) => setIdeaStage(idea.id, e.target.value)}
                      >
                        {STAGES.map((opt) => (
                          <option key={opt.id} value={opt.id}>
                            {opt.label}
                          </option>
                        ))}
                      </select>
                    </li>
                  );
                })}
                {column.length === 0 && (
                  <li className="px-1 py-6 text-center text-xs text-slate-400">Empty</li>
                )}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}
