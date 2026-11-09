import { useEffect, useState } from 'react';
import HubSidebar from '../../features/hub/components/HubSidebar.jsx';
import HubLogo from '../../features/hub/components/HubLogo.jsx';
import SearchModal from '../../features/hub/components/SearchModal.jsx';

export default function HubLayout({
  children,
  mobile,
  setMobile,
  name,
  route,
  go,
  logout,
  approvalCount,
}) {
  const [searchOpen, setSearchOpen] = useState(false);
  const flush = route.kind === 'agent';

  useEffect(() => {
    setMobile(false);
  }, [route.kind, route.channelId, route.tab, setMobile]);

  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="flex h-dvh overflow-hidden bg-slate-50 text-slate-900">
      {mobile && (
        <button
          type="button"
          className="fixed inset-0 z-40 bg-slate-900/30 md:hidden"
          aria-label="Dismiss navigation"
          onClick={() => setMobile(false)}
        />
      )}
      <div
        className={`fixed inset-y-0 left-0 z-50 flex transition-transform duration-200 md:static md:z-auto md:translate-x-0 ${
          mobile ? 'translate-x-0 shadow-xl' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <HubSidebar
          route={route}
          go={go}
          name={name}
          approvalCount={approvalCount}
          openSearch={() => setSearchOpen(true)}
          logout={logout}
          onClose={() => setMobile(false)}
        />
      </div>
      <div className="flex min-w-0 flex-1 flex-col bg-slate-50">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white px-4 py-2.5 md:hidden">
          <button
            type="button"
            onClick={() => setMobile(true)}
            aria-label="Open the menu"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <HubLogo className="h-7 w-7" />
          <span className="flex-1 truncate text-sm font-semibold text-slate-900">
            Personal Agent Hub
          </span>
          <button
            type="button"
            onClick={() => go('agent')}
            className="rounded-lg bg-indigo-50 px-2.5 py-1.5 text-xs font-semibold text-indigo-700"
          >
            Agent
          </button>
          <button
            type="button"
            onClick={() => setSearchOpen(true)}
            aria-label="Search"
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 hover:bg-slate-100"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="7" />
              <path d="M20 20l-3.5-3.5" />
            </svg>
          </button>
        </header>
        <main className={`min-h-0 flex-1 ${flush ? 'overflow-hidden' : 'overflow-y-auto'}`}>
          <div className={flush ? 'h-full' : 'px-4 py-4 md:px-6 md:py-6'}>{children}</div>
        </main>
      </div>
      <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} go={go} />
    </div>
  );
}
