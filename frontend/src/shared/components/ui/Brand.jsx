import { Sparkles } from 'lucide-react';

export default function Brand({ light = false }) {
  return (
    <div
      className={`flex items-center gap-2.5 font-semibold tracking-tight ${light ? 'text-white' : 'text-slate-800'}`}
    >
      <span
        className={`grid size-9 place-items-center rounded-xl ${light ? 'bg-white/15 text-white' : 'bg-brand-600 text-white'}`}
      >
        <Sparkles size={20} />
      </span>
      <span>
        personal<span className={light ? 'text-white/65' : 'text-slate-400'}>agent</span>
        <span className="ml-1 text-brand-500">.</span>
      </span>
    </div>
  );
}
