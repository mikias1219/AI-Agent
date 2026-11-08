const tones = {
  neutral: 'border-white/10 bg-surface-800 text-ink-300',
  accent: 'border-brand-200 bg-brand-50 text-brand-400',
  warning: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
  danger: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
  success: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
};

export default function StatusPill({ label, tone = 'neutral' }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1.5 text-[10px] font-medium ${tones[tone] || tones.neutral}`}
    >
      {label}
    </span>
  );
}
