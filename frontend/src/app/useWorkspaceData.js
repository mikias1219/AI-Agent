import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../shared/api/client.js';

export function useWorkspaceData(authenticated) {
  const [data, setData] = useState({
    status: null,
    tasks: [],
    conversations: [],
    approvals: [],
    activity: [],
    telegramActivity: [],
  });
  const [error, setError] = useState('');
  const generation = useRef(0);
  const refresh = useCallback(async () => {
    if (!authenticated) return;
    const current = generation.current;
    try {
      const [status, tasks, conversations, approvals, activity, telegramActivity] =
        await Promise.all(
          [
            '/status',
            '/tasks',
            '/conversations',
            '/approvals',
            '/activity',
            '/telegram/activity',
          ].map((path) => api(path)),
        );
      if (current !== generation.current) return;
      setData({ status, tasks, conversations, approvals, activity, telegramActivity });
      setError('');
    } catch (e) {
      if (current === generation.current) setError(e.message);
    }
  }, [authenticated]);
  useEffect(() => {
    generation.current += 1;
    if (!authenticated) {
      setData({
        status: null,
        tasks: [],
        conversations: [],
        approvals: [],
        activity: [],
        telegramActivity: [],
      });
      setError('');
      return;
    }
    refresh();
    const timer = setInterval(refresh, 2500);
    return () => {
      generation.current += 1;
      clearInterval(timer);
    };
  }, [authenticated, refresh]);
  return { ...data, error, refresh };
}
