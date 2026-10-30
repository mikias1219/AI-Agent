import { Check, X } from 'lucide-react';

export default function Toast({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div
      role="status"
      className="fixed bottom-6 left-1/2 z-50 flex w-max max-w-[90vw] -translate-x-1/2 items-center gap-3 rounded-2xl bg-slate-800 px-5 py-4 text-xs leading-5 text-white shadow-xl"
    >
      <Check size={15} className="shrink-0 text-brand-200" />
      {message}
      <button aria-label="Dismiss notification" onClick={onDismiss}>
        <X size={14} />
      </button>
    </div>
  );
}
