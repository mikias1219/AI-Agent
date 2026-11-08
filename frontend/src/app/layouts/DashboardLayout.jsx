import { ChevronDown, CircleHelp, LogOut, Menu, X } from 'lucide-react';
import Brand from '../../shared/components/ui/Brand.jsx';
import Avatar from '../../shared/components/ui/Avatar.jsx';
import StatusPill from '../../shared/components/ui/StatusPill.jsx';
import { navSections, pageTitle } from '../routing/navigation.js';

function telegramLabel(telegram) {
  if (!telegram) return 'Unknown';
  if (!telegram.configured) return 'Not configured';
  if (telegram.managed) {
    const runtime = telegram.runtime;
    if (runtime === 'polling') return 'Listening';
    if (runtime === 'responding') return 'Answering';
    if (runtime === 'starting') return 'Starting';
    if (runtime === 'error') return 'Error';
    if (runtime === 'stopped') return 'Stopped';
    return 'Running';
  }
  return 'Configured';
}

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
  const providerLabel = !status
    ? 'Connecting…'
    : status.provider === 'fake'
      ? 'Offline test provider'
      : status.provider === 'hermes'
        ? `Hermes · ${status.model}`
        : status.provider === 'ollama'
          ? `Ollama · ${status.model}`
          : status.model || status.provider;

  return (
    <div className="min-h-screen bg-surface-950">
      <aside
        className={`${mobile ? 'flex' : 'hidden'} fixed inset-y-0 left-0 z-40 w-64 flex-col border-r border-white/10 bg-surface-900 p-5 lg:flex`}
      >
        <div className="flex items-center justify-between">
          <Brand />
          <button
            className="lg:hidden text-ink-400"
            aria-label="Close menu"
            onClick={() => setMobile(false)}
          >
            <X size={20} />
          </button>
        </div>
        <div className="mb-6 mt-8 flex items-center gap-3 rounded-xl border border-white/10 bg-surface-800/70 p-3">
          <Avatar name={name} />
          <div className="min-w-0">
            <p className="truncate text-xs font-semibold text-ink-100">{name}’s workspace</p>
            <p className="mt-1 text-[10px] text-ink-500">Personal account</p>
          </div>
          <ChevronDown className="ml-auto text-ink-500" size={14} />
        </div>
        <nav aria-label="Main navigation" className="flex-1 space-y-5 overflow-y-auto pr-1">
          {navSections.map((section) => (
            <div key={section.id}>
              <p className="eyebrow mb-2 px-3">{section.label}</p>
              <div className="space-y-1">
                {section.items.map(([id, label, Icon]) => (
                  <button
                    key={id}
                    onClick={() => go(id)}
                    aria-current={
                      id === page || (page === 'studio' && id === 'automation') ? 'page' : undefined
                    }
                    className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                      id === page || (page === 'studio' && id === 'automation')
                        ? 'bg-brand-50 font-semibold text-brand-400'
                        : 'text-ink-400 hover:bg-surface-800 hover:text-ink-100'
                    }`}
                  >
                    <Icon size={18} strokeWidth={1.8} />
                    {label}
                    {id === 'tasks' && approvalCount > 0 && (
                      <span className="ml-auto rounded-md bg-surface-950 px-1.5 text-[10px] text-ink-400">
                        {approvalCount}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </nav>
        <div className="mt-4 space-y-3 border-t border-white/10 pt-4">
          <div className="space-y-2 rounded-2xl border border-white/10 bg-surface-800/50 p-3">
            <p className="eyebrow">System status</p>
            <div className="flex flex-wrap gap-2">
              <StatusPill
                label={providerLabel}
                tone={status?.provider === 'fake' ? 'warning' : 'accent'}
              />
              <StatusPill label="Worker · Not connected yet" tone="warning" />
              <StatusPill
                label={`Telegram · ${telegramLabel(status?.telegram)}`}
                tone={status?.telegram?.managed ? 'success' : 'neutral'}
              />
            </div>
          </div>
          <button
            onClick={() =>
              notify(
                'Start with Telegram: verify the bot token, start the bot, and send it a question. Tasks and approvals are shared in this workspace.',
              )
            }
            className="flex w-full items-center gap-3 px-3 py-2 text-xs text-ink-500"
          >
            <CircleHelp size={16} />
            Help & getting started
          </button>
          <button
            onClick={logout}
            className="flex w-full items-center gap-3 px-3 py-2 text-xs text-ink-400"
          >
            <LogOut size={16} />
            Log out
          </button>
        </div>
      </aside>
      {mobile && (
        <button
          aria-label="Dismiss navigation"
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => setMobile(false)}
        />
      )}
      <div className="lg:ml-64">
        <header className="flex h-16 items-center justify-between border-b border-white/10 bg-surface-900/80 px-5 backdrop-blur sm:px-10">
          <div className="flex items-center gap-4 text-xs">
            <button
              className="lg:hidden text-ink-300"
              aria-label="Open menu"
              onClick={() => setMobile(true)}
            >
              <Menu size={21} />
            </button>
            <span className="hidden text-ink-500 sm:block">AURA</span>
            <span className="hidden text-ink-500 sm:block">/</span>
            <span className="text-ink-300">{pageTitle(page)}</span>
          </div>
          <div className="flex items-center gap-4">
            <StatusPill
              label={providerLabel}
              tone={status?.provider === 'fake' ? 'warning' : 'accent'}
            />
            <Avatar name={name} size="size-8" />
          </div>
        </header>
        <main className="mx-auto max-w-[1280px] px-5 py-8 sm:px-10 sm:py-10 xl:px-14">
          {children}
          <footer className="mt-12 flex flex-wrap justify-between gap-3 border-t border-white/10 pt-5 text-[10px] text-ink-500">
            <span>AURA · Personal AI Operating System</span>
            <span>Local worker not connected yet · Real workspace data only</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
