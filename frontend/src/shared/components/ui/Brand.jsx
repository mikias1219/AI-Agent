export default function Brand({ compact = false, light = false }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid size-10 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-sm font-bold text-white shadow-lg shadow-brand-600/40">
        A
      </span>
      {!compact && (
        <div className="min-w-0 leading-tight">
          <p
            className={`text-sm font-semibold tracking-wide ${light ? 'text-white' : 'text-ink-100'}`}
          >
            AURA
          </p>
          <p className={`truncate text-[10px] ${light ? 'text-white/60' : 'text-ink-500'}`}>
            Personal Agent Hub
          </p>
        </div>
      )}
    </div>
  );
}
