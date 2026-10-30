import { useEffect, useState } from 'react';
import { validRoutes } from './navigation.js';

export function useHashRoute() {
  const [page, setPage] = useState(() => {
    const route = window.location.hash.slice(1);
    return validRoutes.includes(route) ? route : 'login';
  });
  useEffect(() => {
    function syncRoute() {
      const route = window.location.hash.slice(1);
      setPage(validRoutes.includes(route) ? route : 'login');
    }
    window.addEventListener('hashchange', syncRoute);
    return () => window.removeEventListener('hashchange', syncRoute);
  }, []);
  function navigate(next) {
    const route = validRoutes.includes(next) ? next : 'login';
    setPage(route);
    window.history.replaceState(null, '', `#${route}`);
    window.scrollTo(0, 0);
  }
  return { page, navigate };
}
