import { useState } from 'react';
import { CHANNELS } from '../channels.js';
import { channelPath } from '../routes.js';
import { inferenceLabel } from '../../../shared/lib/runtime-status.js';

export default function HubDashboardPage({ hub, status, approvals, go, name, onAskAgent }) {
  const [ask, setAsk] = useState('');
  const pending = (approvals || []).filter((a) => a.actionable);
  const tg = status?.telegram;
  const tgListening = ['polling', 'responding', 'starting'].includes(tg?.runtime);
  const first = name ? name.split(' ')[0] : 'there';

  let telegramHint = 'Open Telegram and follow the short guide.';
  if (!tg?.configured) telegramHint = 'Add a bot token, then start the bot.';
  else if (!tgListening && !tg?.managed)
    telegramHint = 'Start the bot, then message it in Telegram.';
  else if (!(tg?.allowed_chat_ids || []).length)
    telegramHint = 'Allow your chat ID, then ask the bot a question.';
  else if (tgListening) telegramHint = 'Bot is listening — message it anytime.';

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <header>
        <h1 className="text-xl font-semibold text-slate-900">Hi {first}</h1>
        <p className="mt-1 text-sm text-slate-500">
          Chat with your agent here or on Telegram. Keep it simple — one clear next step at a time.
        </p>
        <p className="mt-2 text-xs text-slate-400">{inferenceLabel(status)}</p>
        {(status?.provider === 'fake' || status?.active_runtime === 'fake') && (
          <p
            role="status"
            className="mt-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950"
          >
            This cloud server has no Ollama model — chat and Telegram will not give full AI answers
            until you run the agent locally with Ollama. Setup and bot controls still work here.
          </p>
        )}
      </header>

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Ask your agent</h2>
        <p className="mt-1 text-sm text-slate-500">Opens My Agent and sends your message.</p>
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
            placeholder="Type a question…"
            className="min-w-0 flex-1 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-100"
          />
          <button
            type="submit"
            disabled={!ask.trim()}
            className="rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </section>

      <section className="rounded-2xl bg-sky-50 p-5 ring-1 ring-sky-200">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-900">Telegram</h2>
            <p className="mt-1 text-sm text-slate-700">{telegramHint}</p>
          </div>
          <button
            type="button"
            onClick={() => go(channelPath('telegram'))}
            className="rounded-xl bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-700"
          >
            Open guide
          </button>
        </div>
      </section>

      {pending.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-sm font-semibold text-amber-950">
            {pending.length} approval{pending.length === 1 ? '' : 's'} waiting
          </h2>
          <p className="mt-1 text-sm text-amber-900/80">
            The agent needs your OK before continuing.
          </p>
          <button
            type="button"
            onClick={() => go('approvals')}
            className="mt-3 rounded-xl bg-amber-900 px-4 py-2 text-sm font-semibold text-white"
          >
            Review approvals
          </button>
        </section>
      )}

      <section className="rounded-2xl bg-white p-5 ring-1 ring-slate-200">
        <h2 className="text-sm font-semibold text-slate-900">Channels</h2>
        <ul className="mt-3 space-y-2">
          {CHANNELS.filter((c) => c.live).map((c) => (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => go(channelPath(c.id))}
                className="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left hover:bg-slate-50"
              >
                <span className={`size-2.5 rounded-full ${c.color}`} />
                <span className="flex-1 text-sm font-medium text-slate-900">{c.name}</span>
                <span className="text-xs text-slate-400">Ready to set up</span>
              </button>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-400">
          Social apps are listed in the sidebar for later — they are not connected yet.
        </p>
        {/* keep hub reference for google connect status without clutter */}
        {!hub?.google?.connected && (
          <button
            type="button"
            onClick={() => go('connections')}
            className="mt-3 text-sm font-medium text-indigo-600 hover:text-indigo-800"
          >
            Google connections →
          </button>
        )}
      </section>
    </div>
  );
}
