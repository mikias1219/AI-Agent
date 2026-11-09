import { CHANNEL_GROUPS, CHANNELS, channelsInGroup } from '../channels.js';
import { channelPath } from '../routes.js';
import HubLogo from './HubLogo.jsx';

const NAV = [
  {
    id: 'agent',
    label: 'My Agent',
    icon: 'M12 3l2 6h6l-5 4 2 6-5-3.5L7 19l2-6-5-4h6z',
    featured: true,
  },
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: 'M4 13h4v7H4zM10 4h4v16h-4zM16 9h4v11h-4z',
  },
  {
    id: 'roadmap',
    label: 'Ideas & roadmap',
    icon: 'M4 6h16M4 12h10M4 18h6',
  },
  {
    id: 'board',
    label: 'Board',
    icon: 'M5 4h14v10l-6 6H5zM13 20v-6h6',
  },
  {
    id: 'activity',
    label: 'Activity',
    icon: 'M12 8v4l3 3M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z',
  },
];

export default function HubSidebar({
  route,
  go,
  name,
  approvalCount,
  openSearch,
  logout,
  onClose,
}) {
  const activeChannel = route.kind === 'channel' ? route.channelId : null;

  return (
    <aside className="flex h-dvh w-64 shrink-0 flex-col border-r border-slate-200 bg-white">
      <div className="flex items-center gap-2 px-5 pb-4 pt-5">
        <HubLogo className="h-8 w-8" />
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-slate-900">AURA</div>
          <div className="text-xs text-slate-500">Personal Agent Hub</div>
        </div>
        <button
          type="button"
          onClick={() => go('approvals')}
          className="relative rounded-lg p-1.5 text-slate-500 hover:bg-slate-50 hover:text-slate-800"
          aria-label="Approvals"
          title="Approvals"
        >
          <svg
            viewBox="0 0 24 24"
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9M13.73 21a2 2 0 0 1-3.46 0" />
          </svg>
          {approvalCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid size-4 place-items-center rounded-full bg-rose-500 text-[9px] font-bold text-white">
              {approvalCount > 9 ? '9+' : approvalCount}
            </span>
          )}
        </button>
      </div>

      <button
        type="button"
        onClick={openSearch}
        className="mx-3 mb-3 flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-sm text-slate-500 ring-1 ring-slate-200 hover:bg-slate-50 hover:text-slate-800"
      >
        <svg
          viewBox="0 0 24 24"
          className="h-4 w-4"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle cx="11" cy="11" r="7" />
          <path d="M20 20l-3.5-3.5" />
        </svg>
        <span className="flex-1">Search</span>
        <kbd className="rounded border border-slate-200 px-1 text-[10px] text-slate-400">
          Ctrl K
        </kbd>
      </button>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="px-3">
          {CHANNEL_GROUPS.map((g) => (
            <GroupSection
              key={g.id}
              group={g}
              channels={channelsInGroup(g.id)}
              activeId={activeChannel}
              onOpen={(id) => {
                go(channelPath(id));
                onClose?.();
              }}
            />
          ))}
        </div>

        <nav className="mt-6 px-3">
          <div className="px-2 pb-1 text-xs font-semibold uppercase tracking-wide text-slate-400">
            Agent & plan
          </div>
          {NAV.map((n) => {
            const active = route.kind === n.id;
            return (
              <button
                key={n.id}
                type="button"
                onClick={() => {
                  go(n.id);
                  onClose?.();
                }}
                className={`mb-0.5 flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-sm font-medium ${
                  active
                    ? n.featured
                      ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/20'
                      : 'bg-indigo-50 text-indigo-700'
                    : n.featured
                      ? 'bg-indigo-50 text-indigo-800 hover:bg-indigo-100'
                      : 'text-slate-700 hover:bg-slate-50'
                }`}
              >
                <svg
                  viewBox="0 0 24 24"
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <path d={n.icon} />
                </svg>
                {n.label}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => {
              go('connections');
              onClose?.();
            }}
            className={`mt-1 flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-sm font-medium ${
              route.kind === 'connections'
                ? 'bg-indigo-50 text-indigo-700'
                : 'text-slate-700 hover:bg-slate-50'
            }`}
          >
            <svg
              viewBox="0 0 24 24"
              className="h-4 w-4"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            Connections
          </button>
        </nav>
        <p className="mx-5 mt-8 text-xs text-slate-400">
          {CHANNELS.filter((c) => c.live).length} live · {CHANNELS.filter((c) => !c.live).length}{' '}
          scaffolded
        </p>
      </div>

      <div className="flex items-center gap-2 border-t border-slate-200 px-3 py-3">
        <button
          type="button"
          onClick={() => {
            go('account');
            onClose?.();
          }}
          className={`flex min-w-0 flex-1 items-center gap-3 rounded-lg px-2 py-1.5 ${
            route.kind === 'account' || route.kind === 'settings'
              ? 'bg-indigo-50'
              : 'hover:bg-slate-50'
          }`}
        >
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-indigo-100 text-xs font-semibold text-indigo-700">
            {(name || '?').slice(0, 1).toUpperCase()}
          </span>
          <div className="min-w-0 text-left">
            <div className="truncate text-sm font-medium text-slate-900">{name}</div>
            <div className="truncate text-xs text-slate-500">Workspace owner</div>
          </div>
        </button>
        <button
          type="button"
          onClick={logout}
          className="rounded-lg px-2 py-1.5 text-xs text-slate-500 hover:bg-slate-50 hover:text-slate-800"
        >
          Log out
        </button>
      </div>
    </aside>
  );
}

function GroupSection({ group, channels, activeId, onOpen }) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 px-2 pb-1.5 pt-1">
        <svg
          viewBox="0 0 24 24"
          className="h-3.5 w-3.5 text-slate-400"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <path d={group.icon} />
        </svg>
        <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          {group.label}
        </span>
      </div>
      <ul>
        {channels.map((c) => {
          const active = activeId === c.id;
          return (
            <li key={c.id}>
              <button
                type="button"
                onClick={() => onOpen(c.id)}
                className={`flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm ${
                  active ? 'bg-indigo-50 text-indigo-700' : 'text-slate-700 hover:bg-slate-50'
                }`}
              >
                <span className={`size-2.5 shrink-0 rounded-full ${c.color}`} />
                <span className="min-w-0 flex-1 truncate text-left font-medium">{c.name}</span>
                {!c.live && (
                  <span className="text-[10px] font-medium uppercase tracking-wide text-slate-400">
                    Later
                  </span>
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
