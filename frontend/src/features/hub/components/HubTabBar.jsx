export default function HubTabBar({ label, tabs, actions }) {
  return (
    <nav className="mb-5 flex items-end gap-6 border-b border-slate-200" aria-label={label}>
      {tabs.map((t) => (
        <button
          key={t.id}
          type="button"
          onClick={t.onClick}
          aria-current={t.active ? 'page' : undefined}
          className={`-mb-px inline-flex items-center gap-1.5 border-b-2 pb-2.5 text-sm font-medium transition ${
            t.active
              ? 'border-indigo-600 text-indigo-700'
              : 'border-transparent text-slate-500 hover:text-slate-900'
          }`}
        >
          {t.label}
          {!!t.count && (
            <span
              className="rounded-full bg-indigo-600 px-1.5 py-px text-[11px] font-semibold leading-4 text-white tabular-nums"
              aria-label={`${t.count} new`}
            >
              {t.count}
            </span>
          )}
        </button>
      ))}
      {actions && <div className="mb-1.5 ml-auto">{actions}</div>}
    </nav>
  );
}
