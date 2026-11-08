import { Bell, LogOut, Menu, Search, ShieldCheck, Sun, X } from 'lucide-react';
import Brand from '../../shared/components/ui/Brand.jsx';
import Avatar from '../../shared/components/ui/Avatar.jsx';
import { mockupNavItems, pageTitle } from '../routing/navigation.js';

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
  overview = false,
}) {
  const active = (id) =>
    id === page ||
    (page === 'studio' && id === 'automation') ||
    (page === 'approvals' && id === 'approvals');

  return (
    <div className="min-h-screen text-ink-100">
      <aside
        className={`${mobile ? 'flex' : 'hidden'} fixed inset-y-0 left-0 z-40 w-[260px] flex-col border-r border-white/10 bg-surface-900/95 p-4 backdrop-blur-xl lg:flex`}
      >
        <div className="mb-6 flex items-center justify-between px-1">
          <Brand />
          <button
            className="text-ink-400 lg:hidden"
            aria-label="Close menu"
            onClick={() => setMobile(false)}
          >
            <X size={20} />
          </button>
        </div>

        <nav aria-label="Main navigation" className="flex-1 space-y-1 overflow-y-auto pr-1">
          {mockupNavItems.map(([id, label, Icon]) => (
            <button
              key={id}
              onClick={() => go(id)}
              aria-current={active(id) ? 'page' : undefined}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${
                active(id) ? 'nav-active' : 'text-ink-400 hover:bg-white/5 hover:text-ink-100'
              }`}
            >
              <Icon size={18} strokeWidth={1.8} />
              <span className="truncate">{label}</span>
              {id === 'approvals' && approvalCount > 0 && (
                <span className="ml-auto rounded-full bg-aura-rose px-1.5 text-[10px] font-semibold text-white">
                  {approvalCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="mt-3 space-y-3 border-t border-white/10 pt-3">
          <div className="glass flex items-start gap-3 p-3">
            <span className="mt-0.5 rounded-lg bg-aura-emerald/15 p-2 text-aura-emerald">
              <ShieldCheck size={16} />
            </span>
            <div>
              <p className="text-xs font-semibold text-ink-100">Privacy First</p>
              <p className="mt-1 text-[10px] leading-4 text-ink-500">
                Local inference by default. No invented activity.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-surface-800/60 p-2.5">
            <Avatar name={name} size="size-9" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold">{name}</p>
              <p className="truncate text-[10px] text-ink-500">Workspace owner</p>
            </div>
            <button
              onClick={logout}
              className="rounded-lg p-2 text-ink-500 hover:bg-white/5 hover:text-ink-200"
              aria-label="Log out"
              title="Log out"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {mobile && (
        <button
          aria-label="Dismiss navigation"
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          onClick={() => setMobile(false)}
        />
      )}

      <div className="lg:ml-[260px]">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-white/10 bg-surface-950/80 px-4 backdrop-blur-xl sm:px-6">
          <button
            className="text-ink-300 lg:hidden"
            aria-label="Open menu"
            onClick={() => setMobile(true)}
          >
            <Menu size={21} />
          </button>

          <label className="relative mx-auto hidden w-full max-w-xl md:block">
            <span className="sr-only">Search</span>
            <Search
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-500"
              size={16}
            />
            <input
              className="field h-10 border-white/10 bg-surface-900/80 pl-10 pr-16 text-sm"
              placeholder="Search workspace…"
              onFocus={() =>
                notify('Search is visual-only for now. Global search arrives in a later phase.')
              }
              readOnly
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 rounded-md border border-white/10 px-1.5 py-0.5 text-[10px] text-ink-500">
              ⌘K
            </span>
          </label>

          {!overview && (
            <span className="hidden text-xs text-ink-400 xl:block">{pageTitle(page)}</span>
          )}

          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            <span className="inline-flex items-center gap-2 rounded-full border border-aura-amber/30 bg-aura-amber/10 px-3 py-1.5 text-[11px] font-medium text-aura-amber">
              <span className="size-1.5 rounded-full bg-aura-amber" />
              Worker Offline
            </span>
            <button
              className="relative rounded-xl border border-white/10 bg-surface-900/80 p-2.5 text-ink-300 hover:text-ink-100"
              aria-label="Approvals"
              onClick={() => go('approvals')}
            >
              <Bell size={16} />
              {approvalCount > 0 && (
                <span className="absolute -right-1 -top-1 grid size-4 place-items-center rounded-full bg-aura-rose text-[9px] font-bold text-white">
                  {approvalCount > 9 ? '9+' : approvalCount}
                </span>
              )}
            </button>
            <button
              className="hidden rounded-xl border border-white/10 bg-surface-900/80 p-2.5 text-ink-300 sm:inline-flex"
              aria-label="Appearance"
              onClick={() => notify('Dark mode is the AURA default. Theme toggle comes later.')}
            >
              <Sun size={16} />
            </button>
            <Avatar name={name} size="size-9" />
          </div>
        </header>

        <main className={overview ? 'p-4 sm:p-6' : 'mx-auto max-w-[1280px] px-5 py-8 sm:px-8'}>
          {children}
        </main>
      </div>
    </div>
  );
}
