import { useEffect, useRef, useState } from 'react';

export function useNotification() {
  const [message, setMessage] = useState('');
  const timer = useRef();
  useEffect(() => () => clearTimeout(timer.current), []);
  function notify(next) {
    setMessage(next);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMessage(''), 5000);
  }
  function dismiss() {
    clearTimeout(timer.current);
    setMessage('');
  }
  return { message, notify, dismiss };
}
