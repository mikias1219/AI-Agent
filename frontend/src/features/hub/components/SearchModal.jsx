import { useEffect, useMemo, useState } from 'react';
import { CHANNELS } from '../channels.js';
import { channelPath } from '../routes.js';

const STATIC = [
  { id: 'agent', label: 'My Agent', path: 'agent' },
  { id: 'dashboard', label: 'Home', path: 'dashboard' },
  { id: 'approvals', label: 'Approvals', path: 'approvals' },
  { id: 'connections', label: 'Connections', path: 'connections' },
  { id: 'settings', label: 'Account', path: 'account' },
  { id: 'activity', label: 'Activity', path: 'activity' },
];

export default function SearchModal({ open, onClose, go }) {
  const [q, setQ] = useState('');
  useEffect(() => {
    if (!open) setQ('');
  }, [open]);
  useEffect(() => {
    if (!open) return undefined;
    function onKey(e) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);
  const results = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const pages = STATIC.filter((p) => !needle || p.label.toLowerCase().includes(needle));
    const channels = CHANNELS.filter(
      (c) =>
        !needle ||
        c.name.toLowerCase().includes(needle) ||
        c.fullName.toLowerCase().includes(needle),
    ).map((c) => ({
      id: `ch-${c.id}`,
      label: `${c.name}${c.live ? '' : ' (coming later)'}`,
      path: channelPath(c.id),
    }));
    return [...pages, ...channels].slice(0, 12);
  }, [q]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[80] flex items-start justify-center bg-slate-900/40 p-4 pt-[12vh]">
      <button
        type="button"
        className="absolute inset-0"
        aria-label="Close search"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg overflow-hidden rounded-2xl bg-white shadow-2xl ring-1 ring-slate-200">
        <input
          autoFocus
          className="w-full border-b border-slate-200 px-4 py-3 text-sm text-slate-900 outline-none placeholder:text-slate-400"
          placeholder="Search channels and pages…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <ul className="max-h-80 overflow-y-auto py-2">
          {results.length === 0 && (
            <li className="px-4 py-3 text-sm text-slate-500">No matches.</li>
          )}
          {results.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                className="flex w-full px-4 py-2.5 text-left text-sm text-slate-800 hover:bg-indigo-50"
                onClick={() => {
                  go(item.path);
                  onClose();
                }}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
