import { CHANNELS } from '../channels.js';
import { channelPath } from '../routes.js';
import GoogleChannelPanel from '../components/GoogleChannelPanel.jsx';

export default function HubConnectionsPage({ hub, status, go, notify }) {
  const gmail = CHANNELS.find((c) => c.id === 'gmail');
  const tg = status?.telegram;
  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Connections</h1>
        <p className="mt-0.5 text-sm text-slate-500">
          Turn channels on. Telegram is ready to use; Google needs OAuth keys; social is later.
        </p>
      </header>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Telegram</h2>
            <p className="mt-1 text-sm text-slate-500">
              {tg?.configured
                ? 'Token is set. Open the guide to start the bot and chat.'
                : 'Add TELEGRAM_BOT_TOKEN in backend/.env, restart, then open the guide.'}
            </p>
          </div>
          <button
            type="button"
            className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-semibold text-white"
            onClick={() => go(channelPath('telegram'))}
          >
            Open Telegram guide
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

      <section className="rounded-2xl bg-slate-50 p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Other channels</h2>
        <p className="mt-1 text-sm text-slate-500">Listed for later — not connected yet.</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {CHANNELS.filter((c) => !c.live).map((c) => (
            <li
              key={c.id}
              className="inline-flex items-center gap-1.5 rounded-full bg-white px-2.5 py-1 text-xs font-medium text-slate-600 ring-1 ring-slate-200"
            >
              <span className={`size-1.5 rounded-full ${c.color}`} />
              {c.name}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
