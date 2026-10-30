import { useEffect, useRef, useState } from 'react';
import { api, streamChat } from '../../../shared/api/client.js';

export function useAgentChat(authenticated, notify, refresh) {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [busy, setBusy] = useState(false);
  const request = useRef(null);
  const session = useRef(null);
  const generation = useRef(0);
  useEffect(() => {
    if (!authenticated) {
      generation.current += 1;
      request.current?.abort();
      request.current = null;
      session.current = null;
      setMessages([]);
      setSessionId(null);
      setBusy(false);
    }
    return () => {
      generation.current += 1;
      request.current?.abort();
    };
  }, [authenticated]);
  async function send(text) {
    if (!text.trim() || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const current = generation.current;
    setBusy(true);
    setMessages((previous) => [
      ...previous,
      { role: 'user', content: text },
      { role: 'assistant', content: '', streaming: true },
    ]);
    try {
      const data = await streamChat(
        { text, session_id: session.current },
        (token) => {
          if (current !== generation.current) return;
          setMessages((previous) =>
            previous.map((message, index) =>
              index === previous.length - 1
                ? { ...message, content: message.content + token }
                : message,
            ),
          );
        },
        controller.signal,
      );
      if (current !== generation.current) return;
      session.current = data.session_id;
      setSessionId(data.session_id);
      setMessages((previous) =>
        previous.map((message, index) =>
          index === previous.length - 1 ? { role: 'assistant', content: data.reply } : message,
        ),
      );
    } catch (e) {
      if (e.name !== 'AbortError' && current === generation.current) {
        notify(e.message);
        setMessages((previous) =>
          previous
            .filter((message, index) => index !== previous.length - 1 || message.content)
            .map((message, index) =>
              index === previous.length - 1 && message.streaming
                ? { ...message, streaming: false, incomplete: true }
                : message,
            ),
        );
      }
    } finally {
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
        refresh();
      }
    }
  }
  async function load(id) {
    if (request.current) return;
    setBusy(true);
    const controller = new AbortController();
    request.current = controller;
    const current = generation.current;
    try {
      const data = await api(`/conversations/${encodeURIComponent(id)}/messages`, {
        signal: controller.signal,
      });
      if (current !== generation.current) return;
      session.current = id;
      setSessionId(id);
      setMessages(data.filter((m) => ['user', 'assistant'].includes(m.role) && m.content));
    } catch (e) {
      if (e.name !== 'AbortError') notify(e.message);
    } finally {
      if (request.current === controller) {
        request.current = null;
        setBusy(false);
      }
    }
  }
  function newConversation() {
    if (request.current) return;
    session.current = null;
    setSessionId(null);
    setMessages([]);
  }
  return { messages, sessionId, busy, send, load, newConversation };
}
