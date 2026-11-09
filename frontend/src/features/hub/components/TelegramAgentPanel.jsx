import { useMemo, useState } from 'react';
import { api } from '../../../shared/api/client.js';

const PHASES = {
  unknown: { label: 'Not running', tone: 'slate' },
  starting: { label: 'Starting…', tone: 'amber' },
  polling: { label: 'Listening for messages', tone: 'emerald' },
  responding: { label: 'Replying now…', tone: 'indigo' },
  stopped: { label: 'Stopped', tone: 'slate' },
  stale: { label: 'Stopped responding', tone: 'amber' },
  error: { label: 'Error — check token', tone: 'rose' },
};

const TONE = {
  slate: 'bg-slate-100 text-slate-700 ring-slate-200',
  amber: 'bg-amber-50 text-amber-900 ring-amber-200',
  emerald: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  indigo: 'bg-indigo-50 text-indigo-800 ring-indigo-200',
  rose: 'bg-rose-50 text-rose-800 ring-rose-200',
};

function eventLabel(event) {
  if (event === 'security.telegram_unauthorized_chat') return 'Blocked chat (not allowed yet)';
  if (event === 'telegram.reply_sent') return 'Agent replied';
  if (event === 'telegram.reply_send_failed') return 'Reply failed to send';
  if (event === 'telegram.identity_verified') return 'Bot token verified';
  return (event || '').replace(/^telegram\./, '').replaceAll('_', ' ');
}

export default function TelegramAgentPanel({
  telegram,
  events = [],
  refresh,
  notify,
  openConversation,
  goAgent,
}) {
  const [busy, setBusy] = useState('');
  const [identity, setIdentity] = useState(null);
  const [stopping, setStopping] = useState(false);

  const state = telegram?.runtime || 'unknown';
  const phase = PHASES[state] || PHASES.unknown;
  const configured = !!telegram?.configured;
  const allowlist = telegram?.allowed_chat_ids || [];
  const listening = ['starting', 'polling', 'responding'].includes(state);
  const username = identity?.username || telegram?.username;

  const blockedChats = useMemo(() => {
    const ids = new Set();
    for (const e of events) {
      if (e.event === 'security.telegram_unauthorized_chat' && e.details?.chat_id != null) {
        ids.add(String(e.details.chat_id));
      }
    }
    return [...ids];
  }, [events]);

  const next = useMemo(() => {
    if (!configured) {
      return {
        step: 1,
        title: 'Add your bot token',
        body: 'In Telegram, talk to @BotFather → /newbot. Put the token in backend/.env as TELEGRAM_BOT_TOKEN, then restart the dashboard.',
        action: null,
      };
    }
    if (!listening && !telegram?.managed) {
      return {
        step: 2,
        title: 'Start the bot',
        body: 'When it is running, message your bot in Telegram. The same agent that chats here will reply there.',
        action: 'start',
        actionLabel: 'Start bot',
      };
    }
    if (allowlist.length === 0) {
      return {
        step: 3,
        title: 'Allow your chat',
        body:
          blockedChats.length > 0
            ? `Send /start to your bot, then add this chat ID to TELEGRAM_ALLOWED_CHAT_IDS in backend/.env and restart: ${blockedChats[0]}`
            : 'Send /start to your bot. If replies are blocked, your chat ID appears below — add it to TELEGRAM_ALLOWED_CHAT_IDS and restart.',
        action: null,
      };
    }
    if (listening || telegram?.managed) {
      return {
        step: 4,
        title: 'Ask anything in Telegram',
        body: 'Open your bot and send a normal message. Use /help for tips, /new to start a fresh chat. Replies show up here under Recent replies.',
        action: null,
      };
    }
    return {
      step: 2,
      title: 'Start the bot',
      body: 'Start listening so Telegram messages reach your agent.',
      action: 'start',
      actionLabel: 'Start bot',
    };
  }, [configured, listening, telegram?.managed, allowlist.length, blockedChats]);

  async function action(name) {
    setBusy(name);
    try {
      const result = await api(`/telegram/${name}`, { method: 'POST' });
      if (name === 'verify') {
        setIdentity(result);
        notify(
          result.username
            ? `Connected as @${result.username}. No message was sent.`
            : 'Bot token looks valid.',
        );
      } else if (name === 'start') {
        setStopping(false);
        notify('Bot is starting. Status updates in a few seconds.');
      } else {
        setStopping(true);
        notify('Stopping after the current reply finishes.');
      }
      await refresh();
    } catch (e) {
      notify(e.message);
    } finally {
      setBusy('');
    }
  }

  const recent = events.slice(0, 12);

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <section className="rounded-2xl bg-white p-6 ring-1 ring-slate-200">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
              What this agent does
            </p>
            <h2 className="mt-1 text-lg font-semibold text-slate-900">
              You message the bot → AURA replies
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Same agent as <strong>My Agent</strong> in this hub. Only chats you allow get answers.
              Nothing is invented here — status below is live.
            </p>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 ${TONE[phase.tone]}`}
            role="status"
          >
            {stopping && telegram?.managed ? 'Stopping…' : phase.label}
          </span>
        </div>

        {(username || configured) && (
          <p className="mt-4 text-sm text-slate-500">
            {username ? (
              <>
                Bot: <span className="font-medium text-slate-800">@{username}</span>
              </>
            ) : (
              'Bot token is set (hidden).'
            )}
            {allowlist.length > 0 && (
              <>
                {' '}
                · Allowed chats:{' '}
                <span className="font-medium text-slate-800">{allowlist.join(', ')}</span>
              </>
            )}
          </p>
        )}
      </section>

      <section className="rounded-2xl border border-indigo-200 bg-indigo-50/80 p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
          Next step · {next.step} of 4
        </p>
        <h3 className="mt-1 text-base font-semibold text-slate-900">{next.title}</h3>
        <p className="mt-2 text-sm leading-6 text-slate-700">{next.body}</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {next.action === 'start' && (
            <button
              type="button"
              disabled={!!busy || !configured}
              onClick={() => action('start')}
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {busy === 'start' ? 'Starting…' : next.actionLabel}
            </button>
          )}
          {configured && !listening && telegram?.managed === false && next.action !== 'start' && (
            <button
              type="button"
              disabled={!!busy}
              onClick={() => action('start')}
              className="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              {busy === 'start' ? 'Starting…' : 'Start bot'}
            </button>
          )}
          {telegram?.managed && (
            <button
              type="button"
              disabled={!!busy || stopping}
              onClick={() => action('stop')}
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              {busy === 'stop' ? 'Stopping…' : 'Stop bot'}
            </button>
          )}
          <button
            type="button"
            disabled={!!busy || !configured}
            onClick={() => action('verify')}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {busy === 'verify' ? 'Checking…' : 'Check token'}
          </button>
          <button
            type="button"
            onClick={refresh}
            className="rounded-xl border border-transparent px-3 py-2.5 text-sm font-medium text-slate-500 hover:text-slate-800"
          >
            Refresh status
          </button>
        </div>
        {telegram?.error_type && state === 'error' && (
          <p role="alert" className="mt-3 text-sm text-rose-700">
            Last error: {telegram.error_type}. Check the token and backend logs, then try Check
            token.
          </p>
        )}
      </section>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-900">Recent replies & events</h3>
          {goAgent && (
            <button
              type="button"
              onClick={goAgent}
              className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
            >
              Open My Agent
            </button>
          )}
        </div>
        <p className="mt-1 text-xs text-slate-500">
          Real activity only. Open a conversation to read what the agent said.
        </p>

        {!recent.length && (
          <p className="mt-6 rounded-xl bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
            No Telegram activity yet. Finish the next step above, then send your bot a message.
          </p>
        )}

        <ul className="mt-3 divide-y divide-slate-100">
          {recent.map((e) => (
            <li
              key={`${e.id}-${e.event}-${e.occurred_at}`}
              className="flex flex-wrap items-center justify-between gap-2 py-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-900">{eventLabel(e.event)}</p>
                <p className="mt-0.5 text-xs text-slate-500">
                  {e.details?.chat_id != null ? `Chat ${e.details.chat_id}` : ''}
                  {e.details?.username ? ` @${e.details.username}` : ''}
                  {e.occurred_at ? ` · ${new Date(e.occurred_at).toLocaleString()}` : ''}
                </p>
              </div>
              {e.details?.session_id && openConversation && (
                <button
                  type="button"
                  className="shrink-0 text-sm font-semibold text-indigo-600 hover:text-indigo-800"
                  onClick={() => openConversation(e.details.session_id)}
                >
                  Read reply →
                </button>
              )}
            </li>
          ))}
        </ul>

        {blockedChats.length > 0 && (
          <div className="mt-4 rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-950 ring-1 ring-amber-200">
            <p className="font-medium">Chat waiting to be allowed</p>
            <p className="mt-1 text-amber-900/90">
              Add to <code className="rounded bg-white/80 px-1">TELEGRAM_ALLOWED_CHAT_IDS</code>:{' '}
              <strong>{blockedChats.join(', ')}</strong>, then restart and Start bot again.
            </p>
          </div>
        )}
      </section>

      <details className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600 ring-1 ring-slate-200">
        <summary className="cursor-pointer font-medium text-slate-800">More tips</summary>
        <ul className="mt-3 list-disc space-y-2 pl-5 leading-6">
          <li>
            Run either this hub’s bot or <code>personal-agent telegram</code> in a terminal — not
            both.
          </li>
          <li>
            Cloud deploy often uses a test model; for smart replies run the dashboard locally with
            Ollama.
          </li>
          <li>Approvals for tools appear under Requests if the agent needs your OK.</li>
        </ul>
      </details>
    </div>
  );
}
