import { Check, X } from 'lucide-react';

export default function Toast({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div
      role="status"
      className="fixed bottom-6 left-1/2 z-50 flex w-max max-w-[90vw] -translate-x-1/2 items-center gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-3.5 text-sm leading-5 text-slate-800 shadow-xl shadow-slate-900/10"
    >
      <span className="grid size-6 shrink-0 place-items-center rounded-full bg-emerald-50 text-emerald-600">
        <Check size={14} />
      </span>
      {message}
      <button
        type="button"
        aria-label="Dismiss notification"
        className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700"
        onClick={onDismiss}
      >
        <X size={14} />
      </button>
    </div>
  );
}
