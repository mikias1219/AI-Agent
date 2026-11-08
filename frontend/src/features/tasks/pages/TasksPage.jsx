import { useState } from 'react';
import PageHeading from '../../../shared/components/ui/PageHeading.jsx';
import { api } from '../../../shared/api/client.js';

const nextStates = {
  planned: ['in_progress', 'cancelled'],
  in_progress: ['blocked', 'done', 'cancelled'],
  blocked: ['in_progress', 'cancelled'],
  done: [],
  cancelled: [],
};

export default function TasksPage({
  tasks,
  approvals,
  refresh,
  notify,
  decide,
  focusApprovals = false,
}) {
  const [title, setTitle] = useState('');
  const [busy, setBusy] = useState(false);
  async function create(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await api('/tasks', { method: 'POST', body: { title: title.trim() } });
      setTitle('');
      await refresh();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function change(id, status) {
    setBusy(true);
    try {
      await api(`/tasks/${id}`, { method: 'PATCH', body: { status } });
      await refresh();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="Make room for what matters"
        title={focusApprovals ? 'Approvals' : 'Tasks & Goals'}
      >
        {focusApprovals
          ? 'Review agent actions that need your decision.'
          : 'Track work now. Goals arrive in a later phase. Approvals for agent actions stay here.'}
      </PageHeading>
      {!focusApprovals && (
        <>
          <form className="card mb-6 flex flex-wrap gap-3 p-5" onSubmit={create}>
            <label className="sr-only" htmlFor="task-title">
              New task
            </label>
            <input
              id="task-title"
              className="field min-w-0 flex-1"
              placeholder="What needs to get done?"
              maxLength={256}
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <button className="primary" disabled={busy || !title.trim()}>
              Add task
            </button>
          </form>
          <section className="card p-6">
            <h2 className="mb-4 font-semibold">Your tasks</h2>
            {!tasks.length && (
              <p className="py-6 text-sm text-ink-400">No tasks yet. Add one above.</p>
            )}
            {tasks.map((t) => (
              <div
                key={t.id}
                className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 py-4 last:border-0"
              >
                <div>
                  <h3 className="text-sm font-medium">{t.title}</h3>
                  <p className="mt-1 text-xs text-ink-400">{t.status.replaceAll('_', ' ')}</p>
                </div>
                {nextStates[t.status]?.length > 0 && (
                  <select
                    aria-label={`Change status of ${t.title}`}
                    className="field w-auto text-xs"
                    value=""
                    disabled={busy}
                    onChange={(e) => change(t.id, e.target.value)}
                  >
                    <option value="" disabled>
                      Change status…
                    </option>
                    {nextStates[t.status].map((s) => (
                      <option key={s} value={s}>
                        {s.replaceAll('_', ' ')}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            ))}
          </section>
        </>
      )}
      <section className={`card p-6 ${focusApprovals ? '' : 'mt-6'}`}>
        {!focusApprovals && (
          <>
            <p className="eyebrow mb-2">Coming later</p>
            <p className="mb-4 text-xs text-ink-500">
              Goal tracking is not available yet. Pending approvals below are live.
            </p>
          </>
        )}
        <h2 className="font-semibold">Pending approvals</h2>
        {!approvals.length && (
          <p className="mt-4 text-sm text-ink-400">Nothing waiting for your decision.</p>
        )}
        {approvals.map((a) => (
          <div key={a.id} className="border-b border-white/10 py-5 last:border-0">
            <h3 className="text-sm font-medium">{a.tool_name}</h3>
            <pre className="my-3 overflow-auto whitespace-pre-wrap text-xs text-ink-400">
              {JSON.stringify(a.arguments, null, 2)}
            </pre>
            {a.actionable ? (
              <div className="flex gap-3">
                <button className="primary" onClick={() => decide(a.id, true)}>
                  Approve
                </button>
                <button className="secondary" onClick={() => decide(a.id, false)}>
                  Deny
                </button>
              </div>
            ) : (
              <p className="text-xs text-ink-400">
                The original turn is no longer waiting. Ask the agent to retry this action.
              </p>
            )}
          </div>
        ))}
      </section>
    </>
  );
}
