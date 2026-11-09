import { CHANNEL_TABS, channelById } from './channels.js';

export const HUB_ROOTS = [
  'dashboard',
  'board',
  'roadmap',
  'agent',
  'settings',
  'activity',
  'connections',
  'account',
  'approvals',
];

export function channelPath(channelId, tab = 'skills') {
  const safe = CHANNEL_TABS.some((t) => t.id === tab) ? tab : 'skills';
  return `channels/${channelId}/${safe}`;
}

export function parseHubHash(hash) {
  const raw = (hash || '').replace(/^#/, '').replace(/^\/+/, '');
  if (!raw || raw === 'today' || raw === 'login' || raw === 'register' || raw === 'reset') {
    return { kind: raw || 'login', channelId: null, tab: null };
  }
  const parts = raw.split('/').filter(Boolean);
  if (parts[0] === 'channels' && parts[1]) {
    const channel = channelById(parts[1]);
    if (!channel) return { kind: 'dashboard', channelId: null, tab: null };
    const tab = CHANNEL_TABS.some((t) => t.id === parts[2]) ? parts[2] : 'skills';
    return { kind: 'channel', channelId: channel.id, tab };
  }
  if (parts[0] === 'telegram') {
    return { kind: 'channel', channelId: 'telegram', tab: 'skills' };
  }
  if (HUB_ROOTS.includes(parts[0])) {
    return { kind: parts[0], channelId: null, tab: null };
  }
  // Legacy AURA routes → hub equivalents
  const legacy = {
    today: 'dashboard',
    tasks: 'roadmap',
    inbox: 'dashboard',
    calendar: 'channels/calendar/skills',
    memory: 'dashboard',
    knowledge: 'dashboard',
    growth: 'roadmap',
    automation: 'board',
    studio: 'board',
  };
  if (legacy[parts[0]]) {
    return parseHubHash(legacy[parts[0]]);
  }
  return { kind: 'dashboard', channelId: null, tab: null };
}

export function hubTitle(route) {
  if (route.kind === 'channel') {
    const ch = channelById(route.channelId);
    const tab = CHANNEL_TABS.find((t) => t.id === route.tab)?.label || 'Skills';
    return ch ? `${ch.name} · ${tab}` : 'Channel';
  }
  const titles = {
    dashboard: 'Dashboard',
    board: 'Board',
    roadmap: 'Ideas & roadmap',
    agent: 'My Agent',
    settings: 'Settings',
    activity: 'Activity',
    connections: 'Connections',
    account: 'Account',
    approvals: 'Approvals',
    login: 'Sign in',
    register: 'Register',
    reset: 'Reset password',
  };
  return titles[route.kind] || 'AURA';
}

export function serializeHubRoute(route) {
  if (route.kind === 'channel') return channelPath(route.channelId, route.tab);
  return route.kind;
}
