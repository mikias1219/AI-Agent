import { useState } from 'react';
import { RefreshCw } from 'lucide-react';
import PageHeading from '../../../shared/components/ui/PageHeading.jsx';
import { api } from '../../../shared/api/client.js';
export default function ActivityPage({ events, refresh, notify }) {
  const [older, setOlder] = useState([]);
  const [busy, setBusy] = useState(false);
  const [end, setEnd] = useState(false);
  const all = [...events, ...older]
    .filter((e, i, rows) => rows.findIndex((r) => r.id === e.id) === i)
    .sort((a, b) => b.id - a.id);
  async function load() {
    setBusy(true);
    try {
      const rows = await api(`/activity?limit=100&offset=${all.length}`);
      setOlder((prev) => [...prev, ...rows]);
      setEnd(rows.length < 100);
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="A clear trail of real actions"
        title="Every little step, in one place."
        action={
          <button
            className="secondary"
            onClick={() => {
              setOlder([]);
              setEnd(false);
              refresh();
            }}
          >
            <RefreshCw size={15} />
            Refresh
          </button>
        }
      >
        Your agent’s actual chat, tool, task, approval, and Telegram events. Chat text is kept in
        conversation history.
      </PageHeading>
      <section className="card px-6">
        {!all.length && <p className="py-10 text-sm text-slate-500">No activity yet.</p>}
        {all.map((e) => (
          <div key={e.id} className="border-b border-slate-100 py-5 last:border-0">
            <div className="flex flex-wrap justify-between gap-2">
              <h2 className="text-sm font-medium">
                {e.event.replaceAll('_', ' ').replaceAll('.', ' · ')}
              </h2>
              <time className="text-xs text-slate-400">
                {new Date(e.occurred_at).toLocaleString()}
              </time>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {e.actor}
              {e.details.chat_id ? ` · Chat ${e.details.chat_id}` : ''}
            </p>
            <details className="mt-2 text-xs text-slate-500">
              <summary className="cursor-pointer">Details</summary>
              <pre className="mt-2 overflow-auto whitespace-pre-wrap">
                {JSON.stringify(e.details, null, 2)}
              </pre>
            </details>
          </div>
        ))}
      </section>
      {all.length >= 100 && !end && (
        <button className="secondary mt-5" disabled={busy} onClick={load}>
          {busy ? 'Loading…' : 'Load older events'}
        </button>
      )}
    </>
  );
}
