export async function api(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    credentials: 'same-origin',
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  let data;
  try {
    data = await response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw error;
    throw new Error('The backend returned an unreadable response.');
  }
  if (!response.ok) {
    if (response.status === 401 && path !== '/login')
      window.dispatchEvent(new Event('session-expired'));
    const detail = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join('. ')
      : data.detail;
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return data;
}

export async function streamChat(body, onToken, signal) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    credentials: 'same-origin',
    signal,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('session-expired'));
    const error = await response.json();
    throw new Error(
      typeof error.detail === 'string' ? error.detail : 'Could not start the agent reply.',
    );
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  function consume(line) {
    if (!line.trim()) return null;
    const event = JSON.parse(line);
    if (event.type === 'delta') onToken(event.text);
    if (event.type === 'error') throw new Error(event.detail);
    return event.type === 'done' ? event : null;
  }
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let newline;
      while ((newline = buffer.indexOf('\n')) >= 0) {
        const event = consume(buffer.slice(0, newline));
        buffer = buffer.slice(newline + 1);
        if (event) return event;
      }
      if (done) {
        const event = consume(buffer);
        if (event) return event;
        break;
      }
    }
    throw new Error('The model connection ended before the answer was complete.');
  } finally {
    reader.releaseLock();
  }
}
