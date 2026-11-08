export default function EmptyState({ title, children }) {
  return (
    <div className="rounded-2xl border border-dashed border-white/10 bg-surface-900/60 px-5 py-8 text-center">
      <p className="text-sm font-medium text-ink-100">{title}</p>
      {children && (
        <p className="mx-auto mt-2 max-w-md text-xs leading-6 text-ink-400">{children}</p>
      )}
    </div>
  );
}
