import { useState } from 'react';
import { api } from '../../../shared/api/client.js';

export default function HubTelegramControls({ telegram, events, refresh, notify }) {
  const [busy, setBusy] = useState('');
  const [identity, setIdentity] = useState(null);
  const state = telegram?.runtime || 'unknown';
  const phases = {
    unknown: 'Not started',
    starting: 'Starting',
    polling: 'Listening',
    responding: 'Answering',
    stopped: 'Stopped',
    stale: 'Heartbeat expired',
    error: 'Connection error',
  };

  async function action(name) {
    setBusy(name);
    try {
      const result = await api(`/telegram/${name}`, { method: 'POST' });
      if (name === 'verify') {
        setIdentity(result);
        notify(
          `Telegram verified${result.username ? ` as @${result.username}` : ''}. No message was sent.`,
        );
      } else {
        notify(
          name === 'start'
            ? 'Bot start requested. Watching for its heartbeat.'
            : 'Stopping after the current poll or response completes.',
        );
      }
      await refresh();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy('');
    }
  }

  return (
    <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Telegram runtime</h2>
          <p className="mt-1 text-sm text-slate-500" role="status">
            {identity?.username || telegram?.username
              ? `@${identity?.username || telegram.username} · `
              : ''}
            {phases[state] || state}
          </p>
        </div>
        <button
          type="button"
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          onClick={refresh}
        >
          Refresh
        </button>
      </div>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-xs text-slate-500">Bot token</dt>
          <dd className="mt-0.5 text-slate-800">
            {telegram?.configured ? 'Configured · hidden' : 'Not configured'}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Allowed chats</dt>
          <dd className="mt-0.5 break-words text-slate-800">
            {telegram?.allowed_chat_ids?.join(', ') || 'None · replies blocked'}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-slate-500">Last heartbeat</dt>
          <dd className="mt-0.5 text-slate-800">
            {telegram?.last_seen ? new Date(telegram.last_seen).toLocaleTimeString() : 'Not seen'}
          </dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={!!busy || !telegram?.configured}
          onClick={() => action('verify')}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 disabled:opacity-50"
        >
          {busy === 'verify' ? 'Checking…' : 'Verify bot token'}
        </button>
        <button
          type="button"
          disabled={!!busy || !telegram?.configured}
          onClick={() => action('start')}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busy === 'start' ? 'Starting…' : 'Start bot'}
        </button>
        <button
          type="button"
          disabled={!!busy || !telegram?.managed}
          onClick={() => action('stop')}
          className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm font-medium text-slate-700 disabled:opacity-50"
        >
          {busy === 'stop' ? 'Stopping…' : 'Stop bot'}
        </button>
      </div>
      {(events || []).length > 0 && (
        <div className="mt-5 border-t border-slate-100 pt-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Recent Telegram activity
          </h3>
          <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto text-xs text-slate-600">
            {events.slice(0, 20).map((ev) => (
              <li key={`${ev.id || ev.occurred_at}-${ev.event}`}>
                <span className="text-slate-400">
                  {ev.occurred_at ? new Date(ev.occurred_at).toLocaleString() : ''}
                </span>{' '}
                {ev.event}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
