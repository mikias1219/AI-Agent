import { useState } from 'react';
import { Play, Square, RefreshCw, ShieldCheck } from 'lucide-react';
import PageHeading from '../../../shared/components/ui/PageHeading.jsx';
import AppMark from '../../../shared/components/ui/AppMark.jsx';
import { api } from '../../../shared/api/client.js';

export default function TelegramPage({ telegram, events, refresh, notify, openConversation }) {
  const [busy, setBusy] = useState('');
  const [identity, setIdentity] = useState(null);
  const [stopping, setStopping] = useState(false);
  const state = telegram?.runtime || 'unknown';
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
        setStopping(name === 'stop');
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
  const phases = {
    unknown: 'Not started',
    starting: 'Starting',
    polling: 'Listening',
    responding: 'Answering',
    stopped: 'Stopped',
    stale: 'Heartbeat expired',
    error: 'Connection error',
  };
  return (
    <>
      <PageHeading
        eyebrow="Your first connected app"
        title="Your agent, right in Telegram."
        action={
          <button className="secondary" onClick={refresh}>
            <RefreshCw size={15} />
            Refresh
          </button>
        }
      >
        Chat with the same agent and follow its work here.
      </PageHeading>
      <div className="grid items-start gap-6 xl:grid-cols-[1.05fr_1fr]">
        <section className="card p-6">
          <div className="flex items-center gap-4">
            <AppMark id="telegram" size="size-12" />
            <div>
              <h2 className="font-semibold">
                {identity?.username || telegram?.username
                  ? `@${identity?.username || telegram.username}`
                  : 'Telegram bot'}
              </h2>
              <p className="mt-1 text-sm text-slate-500" role="status">
                {stopping && telegram?.managed ? 'Stopping…' : phases[state] || state}
              </p>
            </div>
          </div>
          <dl className="my-6 space-y-4 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Bot token</dt>
              <dd>{telegram?.configured ? 'Configured · hidden' : 'Not configured'}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Allowed chats</dt>
              <dd className="max-w-52 break-words text-right">
                {telegram?.allowed_chat_ids?.join(', ') || 'None · replies blocked'}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Last heartbeat</dt>
              <dd>
                {telegram?.last_seen
                  ? new Date(telegram.last_seen).toLocaleTimeString()
                  : 'Not seen'}
              </dd>
            </div>
          </dl>
          <div className="flex flex-wrap gap-3">
            <button
              className="secondary"
              disabled={!!busy || !telegram?.configured}
              onClick={() => action('verify')}
            >
              {busy === 'verify' ? 'Checking…' : 'Verify bot token'}
            </button>
            {telegram?.managed ? (
              <button
                className="secondary"
                disabled={!!busy || stopping}
                onClick={() => action('stop')}
              >
                <Square size={14} />
                Stop bot
              </button>
            ) : (
              <button
                className="primary"
                disabled={
                  !!busy ||
                  !telegram?.configured ||
                  ['starting', 'polling', 'responding'].includes(state)
                }
                onClick={() => {
                  setStopping(false);
                  action('start');
                }}
              >
                <Play size={15} />
                {busy === 'start' ? 'Starting…' : 'Start bot'}
              </button>
            )}
          </div>
          {telegram?.error_type && state === 'error' && (
            <p role="alert" className="mt-4 text-sm text-rose-600">
              Last error: {telegram.error_type}. Verify the token and check the backend terminal.
            </p>
          )}
          <p className="mt-5 text-xs leading-6 text-slate-500">
            <ShieldCheck className="mr-1 inline text-emerald-600" size={14} />
            Only allowed chats receive replies. Starting with an empty allowlist records incoming
            chat IDs without replying.
          </p>
        </section>
        <section className="card p-6">
          <h2 className="font-semibold">Get your first reply</h2>
          <ol className="mt-5 space-y-5 text-sm leading-6 text-slate-600">
            <li>
              <b className="text-slate-800">1. Create a bot.</b> Open @BotFather in Telegram, use
              /newbot, and put its token in <code>backend/.env</code> as TELEGRAM_BOT_TOKEN.
            </li>
            <li>
              <b className="text-slate-800">2. Restart this dashboard.</b> Click Start bot, then
              send /start to your bot. If your chat is not allowed yet, its ID appears below as a
              blocked chat.
            </li>
            <li>
              <b className="text-slate-800">3. Allow your chat.</b> Add that numeric ID to
              TELEGRAM_ALLOWED_CHAT_IDS in backend/.env. Restart the dashboard, start the bot, and
              ask a question.
            </li>
          </ol>
          <p className="mt-5 rounded-xl bg-brand-50 p-4 text-xs leading-6 text-brand-700">
            Use /help for a short guide and /new for a fresh conversation. Run either the dashboard
            bot or the CLI bot, not both. The dashboard stops its own bot when it shuts down.
          </p>
        </section>
      </div>
      <section className="card mt-6 p-6">
        <h2 className="font-semibold">Telegram activity</h2>
        <p className="mt-1 text-xs text-slate-500">
          Actual replies, blocked chats, verification, and delivery errors.
        </p>
        {!events.length && (
          <p className="py-10 text-sm text-slate-500">
            No Telegram events yet. Start the bot and send it a message.
          </p>
        )}
        {events.map((e) => (
          <div
            key={e.id}
            className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 py-4 last:border-0"
          >
            <div>
              <p className="text-sm font-medium">
                {e.event === 'security.telegram_unauthorized_chat'
                  ? 'Blocked chat'
                  : e.event.replace('telegram.', '').replaceAll('_', ' ')}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {e.details.chat_id
                  ? `Chat ID: ${e.details.chat_id}`
                  : e.details.username
                    ? `@${e.details.username}`
                    : ''}{' '}
                · {new Date(e.occurred_at).toLocaleString()}
              </p>
            </div>
            {e.details.session_id && (
              <button
                className="text-xs font-semibold text-brand-600"
                onClick={() => openConversation(e.details.session_id)}
              >
                Read conversation →
              </button>
            )}
          </div>
        ))}
      </section>
    </>
  );
}
