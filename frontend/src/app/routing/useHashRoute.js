import { useEffect, useState } from 'react';
import { authRoutes } from './navigation.js';
import { parseHubHash, serializeHubRoute } from '../../features/hub/routes.js';

function readRoute() {
  return parseHubHash(window.location.hash.slice(1));
}

export function useHashRoute() {
  const [route, setRoute] = useState(readRoute);
  useEffect(() => {
    function syncRoute() {
      setRoute(readRoute());
    }
    window.addEventListener('hashchange', syncRoute);
    return () => window.removeEventListener('hashchange', syncRoute);
  }, []);
  function navigate(next) {
    let target;
    if (typeof next === 'string') {
      target = parseHubHash(next);
    } else {
      target = next;
    }
    if (authRoutes.includes(target.kind) || target.kind) {
      setRoute(target);
      window.history.replaceState(null, '', `#${serializeHubRoute(target)}`);
      window.scrollTo(0, 0);
    }
  }
  return {
    route,
    page: route.kind,
    channelId: route.channelId,
    tab: route.tab,
    navigate,
  };
}
