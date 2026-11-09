import { useState } from 'react';
import { CHANNELS } from '../channels.js';

export default function HubBoardPage({ hub, channelId = null, notify }) {
  const [text, setText] = useState('');
  const notes = (hub.boardNotes || []).filter((n) =>
    channelId ? n.channelId === channelId : true,
  );

  async function addNote(e) {
    e.preventDefault();
    if (!text.trim()) return;
    const note = {
      id: `note-${Date.now()}`,
      channelId: channelId || null,
      text: text.trim(),
      x: 40 + (notes.length % 4) * 24,
      y: 40 + Math.floor(notes.length / 4) * 24,
    };
    try {
      await hub.updateBoardNotes([...(hub.boardNotes || []), note]);
      setText('');
      notify?.('Note saved.');
    } catch (err) {
      notify?.(err.message);
    }
  }

  async function removeNote(id) {
    try {
      await hub.updateBoardNotes((hub.boardNotes || []).filter((n) => n.id !== id));
    } catch (err) {
      notify?.(err.message);
    }
  }

  return (
    <div className="space-y-4">
      {!channelId && (
        <header>
          <h1 className="text-xl font-semibold text-slate-900">Board</h1>
          <p className="mt-0.5 text-sm text-slate-500">
            Scratch notes for content and automation planning across channels.
          </p>
        </header>
      )}
      <form onSubmit={addNote} className="flex flex-wrap gap-2">
        <input
          className="min-w-[16rem] flex-1 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          placeholder="Add a board note…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <button
          type="submit"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
        >
          Add
        </button>
      </form>
      <div className="min-h-[20rem] rounded-2xl bg-slate-100/80 p-4 ring-1 ring-slate-200">
        {notes.length === 0 ? (
          <p className="text-sm text-slate-500">No notes yet. Add one above.</p>
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {notes.map((n) => {
              const ch = CHANNELS.find((c) => c.id === n.channelId);
              return (
                <li key={n.id} className="rounded-xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                      {ch?.name || 'Shared'}
                    </span>
                    <button
                      type="button"
                      className="text-xs text-slate-400 hover:text-rose-600"
                      onClick={() => removeNote(n.id)}
                    >
                      Remove
                    </button>
                  </div>
                  <p className="whitespace-pre-wrap text-sm text-slate-800">{n.text}</p>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
