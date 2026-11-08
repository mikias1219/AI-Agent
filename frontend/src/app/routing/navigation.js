import {
  Activity,
  BookOpen,
  Brain,
  CalendarDays,
  CheckSquare,
  Home,
  Inbox,
  Link2,
  ListTodo,
  Send,
  Settings,
  Sparkles,
  Target,
  Workflow,
} from 'lucide-react';

/** Flat mockup order for the primary sidebar. */
export const mockupNavItems = [
  ['today', 'Overview', Home],
  ['agent', 'My Agent', Sparkles],
  ['tasks', 'Tasks & Goals', ListTodo],
  ['calendar', 'Calendar', CalendarDays],
  ['inbox', 'Unified Inbox', Inbox],
  ['memory', 'Memory', Brain],
  ['knowledge', 'Knowledge Hub', BookOpen],
  ['growth', 'Personal Growth', Target],
  ['automation', 'Automation Studio', Workflow],
  ['connections', 'Integrations', Link2],
  ['approvals', 'Approvals', CheckSquare],
  ['activity', 'Activity & Logs', Activity],
  ['settings', 'Settings', Settings],
];

/** Extra routes kept for deep links / e2e (not always shown in mockup list). */
export const extraNavItems = [['telegram', 'Telegram', Send]];

export const navItems = [...mockupNavItems, ...extraNavItems];

export const authRoutes = ['login', 'register', 'reset'];

export const validRoutes = [...authRoutes, ...navItems.map(([id]) => id), 'studio'];

export function pageTitle(page) {
  if (page === 'studio') return 'Automation Studio';
  if (page === 'approvals') return 'Approvals';
  return navItems.find((item) => item[0] === page)?.[1] || 'Overview';
}

/** @deprecated Prefer mockupNavItems — kept for any leftover imports. */
export const navSections = [{ id: 'main', label: 'Menu', items: mockupNavItems }];
