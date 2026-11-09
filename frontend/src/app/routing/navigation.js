import { hubTitle } from '../../features/hub/routes.js';

export const authRoutes = ['login', 'register', 'reset'];

/** @deprecated Hub sidebar owns navigation; kept for leftover layout imports. */
export const mockupNavItems = [];
export const navItems = [];
export const validRoutes = [...authRoutes, 'dashboard', 'board', 'roadmap', 'agent'];

export function pageTitle(pageOrRoute) {
  if (typeof pageOrRoute === 'object' && pageOrRoute) {
    return hubTitle(pageOrRoute);
  }
  return hubTitle({ kind: pageOrRoute || 'dashboard', channelId: null, tab: null });
}
