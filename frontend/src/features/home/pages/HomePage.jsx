import { ArrowRight, CalendarDays, FileText, Link2, ShieldCheck, WandSparkles } from 'lucide-react';
import AppMark from '../../../shared/components/ui/AppMark.jsx';
import { appList } from '../../../shared/config/app-catalog.js';

export default function HomePage({ name, prompt, setPrompt, ask, busy, send, go, status, tasks }) {
  return (
    <>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
            <span className="text-amber-500">☀</span> A fresh start, at your pace
          </div>
          <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
            Hey {name}, let’s make today easier<span className="text-brand-500">.</span>
          </h1>
          <p className="mt-3 text-sm text-slate-500">
            One workspace for your ideas, your apps, and a little everyday help.
          </p>
        </div>
      </div>
      <section className="relative overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-[#efecff] via-[#f6f4ff] to-[#faf8ff] p-6 sm:p-8">
        <div className="pointer-events-none absolute -right-10 -top-20 size-64 rounded-full border-[25px] border-white/30" />
        <div className="relative">
          <div className="mb-5 flex items-center gap-2 text-sm font-medium text-brand-700">
            <WandSparkles size={18} />
            Your ideas start here
          </div>
          <h2 className="mb-2 text-2xl font-semibold tracking-tight text-[#413960]">
            What can I take off your plate?
          </h2>
          <p className="mb-6 text-sm text-[#9389aa]">
            Tell your agent what you have in mind. A simple sentence is enough.
          </p>
          <form
            onSubmit={ask}
            className="rounded-2xl border border-white bg-white p-3 shadow-lg shadow-brand-200/10"
          >
            <label htmlFor="home-request" className="sr-only">
              Ask your agent
            </label>
            <textarea
              id="home-request"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              className="w-full resize-none border-0 bg-transparent px-3 py-2 text-sm leading-7 focus:outline-none focus:ring-0"
              placeholder="Ask a question, plan a task, or tell me what you need…"
              rows={2}
            />
            <div className="flex flex-wrap items-center justify-between gap-3 px-2">
              <span className="flex items-center gap-1.5 text-[10px] text-slate-400">
                <ShieldCheck size={13} />
                You review. Your agent helps.
              </span>
              <button className="primary py-2.5" type="submit" disabled={busy || !prompt.trim()}>
                Ask my agent
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
          <div className="mt-4 flex flex-wrap gap-2">
            {[
              ['Open Telegram', FileText, () => go('telegram')],
              ['Plan my day', CalendarDays, () => send('Help me plan my day.')],
              ['Explore my apps', Link2, () => go('connections')],
            ].map(([text, Icon, fn]) => (
              <button
                key={text}
                onClick={fn}
                className="flex items-center gap-2 rounded-full border border-white bg-white/55 px-3.5 py-2 text-[11px] text-[#8b7ea1] transition hover:bg-white"
              >
                <Icon size={13} />
                {text}
              </button>
            ))}
          </div>
        </div>
      </section>
      <div className="mb-4 mt-9 flex items-center justify-between">
        <h2 className="font-semibold">A good place to start</h2>
        <span className="text-[11px] text-slate-400">Made for your everyday</span>
      </div>
      <div className="grid gap-5 xl:grid-cols-[1.15fr_1fr]">
        <article className="card p-6">
          <div className="flex items-center justify-between">
            <span className="flex size-10 items-center justify-center rounded-xl bg-orange-50 text-orange-400">
              <FileText size={21} />
            </span>
            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-[10px] text-amber-700">
              Telegram first
            </span>
          </div>
          <h3 className="mt-5 text-lg font-semibold tracking-tight">
            Your everyday agent, on Telegram.
          </h3>
          <p className="mt-2 max-w-sm text-xs leading-6 text-slate-400">
            Ask questions in Telegram, read conversations here, and follow your agent’s delivery
            activity from one workspace.
          </p>
          <div className="my-5 flex items-center gap-2">
            <AppMark id="telegram" size="size-7" />

            <span className="ml-1 text-[10px] text-slate-400">
              Same agent. Shared conversation history.
            </span>
          </div>
          <button
            onClick={() => go('telegram')}
            className="flex w-full items-center justify-between border-t border-slate-100 pt-4 text-xs font-semibold text-brand-600"
          >
            Manage Telegram
            <ArrowRight size={15} />
          </button>
        </article>
        <article className="card p-6">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold">Your apps, a little closer</h3>
            <button onClick={() => go('connections')} className="text-[11px] text-brand-600">
              View all ↗
            </button>
          </div>
          {appList.slice(0, 3).map((a) => (
            <div
              key={a.id}
              className="flex items-center gap-3 border-b border-slate-100 py-4 last:border-0"
            >
              <AppMark id={a.id} size="size-9" />
              <div>
                <p className="text-xs font-medium">{a.name}</p>
                <p className="mt-1 text-[10px] text-slate-400">{a.description}</p>
              </div>
              <span
                className={`ml-auto shrink-0 rounded-full px-2 py-1 text-[9px] ${a.id === 'telegram' ? 'bg-sky-50 text-sky-600' : 'bg-slate-50 text-slate-400'}`}
              >
                {a.id === 'telegram'
                  ? status?.telegram?.configured
                    ? 'Configured'
                    : 'Setup needed'
                  : 'Planned'}
              </span>
            </div>
          ))}
        </article>
      </div>
      <div className="mt-7 flex items-center gap-2 text-[11px] text-slate-400">
        <ShieldCheck size={15} className="text-emerald-500" />
        {tasks.filter((t) => !['done', 'cancelled'].includes(t.status)).length} open task(s).
        Actions that require approval stay under your control.
      </div>
    </>
  );
}
