import { Sparkles } from 'lucide-react';

export default function Brand({ light = false }) {
  return (
    <div
      className={`flex items-center gap-2.5 font-semibold tracking-tight ${light ? 'text-white' : 'text-ink-100'}`}
    >
      <span
        className={`grid size-9 place-items-center rounded-xl ${light ? 'bg-white/15 text-white' : 'bg-brand-600 text-white'}`}
      >
        <Sparkles size={20} />
      </span>
      <span>
        AURA
        <span className={`ml-1 ${light ? 'text-white/50' : 'text-brand-400'}`}>.</span>
      </span>
    </div>
  );
}
