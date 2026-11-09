import { useCallback, useEffect, useState } from 'react';
import { api } from '../../../shared/api/client.js';
import { defaultBoardNotes, defaultIdeas, defaultSkills } from '../channels.js';

const empty = () => ({
  skills: defaultSkills(),
  ideas: defaultIdeas(),
  boardNotes: defaultBoardNotes(),
});

export function useHubState(authenticated) {
  const [state, setState] = useState(empty);
  const [google, setGoogle] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    if (!authenticated) return;
    try {
      const [hub, googleStatus] = await Promise.all([api('/hub/state'), api('/google/status')]);
      setState({
        skills: hub.skills?.length ? hub.skills : defaultSkills(),
        ideas: hub.ideas?.length ? hub.ideas : defaultIdeas(),
        boardNotes: hub.boardNotes?.length ? hub.boardNotes : defaultBoardNotes(),
      });
      setGoogle(googleStatus);
      setError('');
    } catch (e) {
      setError(e.message);
    }
  }, [authenticated]);

  useEffect(() => {
    if (!authenticated) {
      setState(empty());
      setGoogle(null);
      return;
    }
    refresh();
  }, [authenticated, refresh]);

  const save = useCallback(
    async (next) => {
      setSaving(true);
      try {
        const payload = next || state;
        const saved = await api('/hub/state', { method: 'PUT', body: payload });
        setState({
          skills: saved.skills || [],
          ideas: saved.ideas || [],
          boardNotes: saved.boardNotes || [],
        });
        setError('');
      } catch (e) {
        setError(e.message);
        throw e;
      } finally {
        setSaving(false);
      }
    },
    [state],
  );

  async function updateSkills(skills) {
    const next = { ...state, skills };
    setState(next);
    await save(next);
  }

  async function updateIdeas(ideas) {
    const next = { ...state, ideas };
    setState(next);
    await save(next);
  }

  async function updateBoardNotes(boardNotes) {
    const next = { ...state, boardNotes };
    setState(next);
    await save(next);
  }

  return {
    ...state,
    google,
    error,
    saving,
    refresh,
    save,
    updateSkills,
    updateIdeas,
    updateBoardNotes,
  };
}
