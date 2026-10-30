import { ChevronDown, CircleHelp, LogOut, Menu, Sparkles, X } from 'lucide-react';
import Brand from '../../shared/components/ui/Brand.jsx';
import Avatar from '../../shared/components/ui/Avatar.jsx';
import { navItems } from '../routing/navigation.js';

export default function DashboardLayout({
  children,
  mobile,
  setMobile,
  name,
  page,
  go,
  notify,
  logout,
  status,
  approvalCount,
}) {
  return (
    <div className="min-h-screen">
      <aside
        className={`${mobile ? 'flex' : 'hidden'} fixed inset-y-0 left-0 z-40 w-64 flex-col border-r border-slate-200/70 bg-white p-6 lg:flex`}
      >
        <div className="flex items-center justify-between">
          <Brand />
          <button className="lg:hidden" aria-label="Close menu" onClick={() => setMobile(false)}>
            <X size={20} />
          </button>
        </div>
        <div className="mb-8 mt-9 flex items-center gap-3 rounded-xl border border-slate-100 bg-slate-50/70 p-3">
          <Avatar name={name} />
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold">{name}’s workspace</p>
            <p className="mt-1 text-[10px] text-slate-400">Personal account</p>
          </div>
          <ChevronDown className="ml-auto text-slate-400" size={14} />
        </div>
        <p className="eyebrow mb-3 px-3">Your workspace</p>
        <nav aria-label="Main navigation" className="space-y-1.5">
          {navItems.map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => go(id)}
              aria-current={id === page ? 'page' : undefined}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-sm transition ${id === page ? 'bg-brand-50 font-semibold text-brand-600' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              <Icon size={18} strokeWidth={1.8} />
              {label}
              {id === 'tasks' && approvalCount > 0 && (
                <span className="ml-auto rounded-md bg-white px-1.5 text-[10px] text-slate-400">
                  {approvalCount}
                </span>
              )}
            </button>
          ))}
        </nav>
        <div className="mt-auto pt-12">
          <div className="rounded-2xl bg-[#f5f3fd] p-4">
            <span className="text-brand-500">
              <Sparkles size={20} />
            </span>
            <p className="mt-3 text-xs font-semibold text-slate-700">
              Small steps. More possibility.
            </p>
            <p className="mt-2 text-[11px] leading-5 text-slate-400">
              Start with one thing you’d like help with. Your agent takes it from there.
            </p>
          </div>
          <button
            onClick={() =>
              notify(
                'Start with Telegram: verify the bot token, start the bot, and send it a question. Tasks and approvals are shared in this workspace.',
              )
            }
            className="mt-5 flex w-full items-center gap-3 px-3 py-2 text-xs text-slate-400"
          >
            <CircleHelp size={16} />
            Help & getting started
          </button>
          <button
            onClick={logout}
            className="mt-2 flex w-full items-center gap-3 border-t border-slate-100 px-3 pt-5 text-xs text-slate-400"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>
      {mobile && (
        <button
          aria-label="Dismiss navigation"
          className="fixed inset-0 z-30 bg-slate-900/20 lg:hidden"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="lg:ml-64">
        <header className="flex h-20 items-center justify-between border-b border-slate-200/70 bg-white/70 px-5 sm:px-10">
          <div className="flex items-center gap-4 text-xs">
            <button className="lg:hidden" aria-label="Open menu" onClick={() => setMobile(true)}>
              <Menu size={21} />
            </button>
            <span className="hidden text-slate-400 sm:block">My workspace</span>
            <span className="hidden text-slate-300 sm:block">/</span>
            <span className="text-slate-600">{navItems.find((n) => n[0] === page)?.[1]}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="rounded-full border border-brand-100 bg-brand-50 px-3 py-1.5 text-[10px] font-medium text-brand-600">
              {status
                ? status.provider === 'fake'
                  ? 'Offline test provider'
                  : status.model
                : 'Connecting…'}
            </span>
            <Avatar name={name} size="size-8" />
          </div>
        </header>
        <main className="mx-auto max-w-[1280px] px-5 py-8 sm:px-10 sm:py-10 xl:px-14">
          {children}
          <footer className="mt-12 flex flex-wrap justify-between gap-3 border-t border-slate-200/70 pt-5 text-[10px] text-slate-400">
            <span>Made for a calmer everyday.</span>
            <span>Local workspace · Real agent activity</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
