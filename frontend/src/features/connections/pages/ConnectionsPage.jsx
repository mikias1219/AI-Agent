import { ArrowUpRight } from 'lucide-react';
import AppMark from '../../../shared/components/ui/AppMark.jsx';
import PageHeading from '../../../shared/components/ui/PageHeading.jsx';
import { appList } from '../../../shared/config/app-catalog.js';

export default function ConnectionsPage({ go, telegram }) {
  return (
    <>
      <PageHeading
        eyebrow="Everything in good company"
        title="Your favorite apps. One friendly workspace."
      >
        Connect a little at a time. Each app gives your personal agent another way to help.
      </PageHeading>
      <div className="grid gap-5 md:grid-cols-2">
        {appList.map((a) => (
          <article className="card p-6" key={a.id}>
            <div className="flex items-center justify-between">
              <AppMark id={a.id} size="size-12" />
              <span className="rounded-full bg-slate-50 px-3 py-1 text-[10px] text-slate-400">
                {a.id === 'telegram'
                  ? telegram?.configured
                    ? 'Configured'
                    : 'Setup needed'
                  : 'Planned'}
              </span>
            </div>
            <h2 className="mt-5 font-semibold">{a.name}</h2>
            <p className="mt-2 min-h-12 text-sm leading-6 text-slate-400">{a.detail}</p>
            <button
              className="secondary mt-5 w-full"
              onClick={() => go('telegram')}
              disabled={a.id !== 'telegram'}
            >
              {a.id === 'telegram' ? 'Manage Telegram' : 'Coming later'}
              <ArrowUpRight size={14} />
            </button>
          </article>
        ))}
      </div>
      <p className="mt-6 text-xs leading-6 text-slate-400">
        Telegram is implemented first. Google Workspace, LinkedIn, and Facebook are not connected
        yet.
      </p>
    </>
  );
}
