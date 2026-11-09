import { CHANNELS } from '../channels.js';
import { channelPath } from '../routes.js';
import GoogleChannelPanel from '../components/GoogleChannelPanel.jsx';

export default function HubConnectionsPage({ hub, status, go, notify }) {
  const gmail = CHANNELS.find((c) => c.id === 'gmail');
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Connections</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Telegram and Google are live in v1. Social channels are scaffolded only.
        </p>
      </header>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Telegram</h2>
            <p className="mt-1 text-sm text-slate-500">
              {status?.telegram?.configured
                ? 'Bot token configured.'
                : 'Add TELEGRAM_BOT_TOKEN in backend/.env.'}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white"
            onClick={() => go(channelPath('telegram'))}
          >
            Open Telegram agent
          </button>
        </div>
      </section>

      {gmail && (
        <GoogleChannelPanel
          channel={gmail}
          google={hub.google}
          notify={notify}
          refresh={hub.refresh}
        />
      )}

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Social scaffolds</h2>
        <ul className="mt-3 divide-y divide-slate-100">
          {CHANNELS.filter((c) => !c.live).map((c) => (
            <li key={c.id} className="flex items-center justify-between gap-3 py-2.5">
              <div className="flex items-center gap-2">
                <span className={`size-2.5 rounded-full ${c.color}`} />
                <span className="text-sm text-slate-800">{c.name}</span>
              </div>
              <button
                type="button"
                className="text-sm text-indigo-600 hover:text-indigo-800"
                onClick={() => go(channelPath(c.id))}
              >
                View plan
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
