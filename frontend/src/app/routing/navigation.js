import {
  Activity,
  BookOpen,
  Brain,
  CalendarDays,
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

export const navSections = [
  {
    id: 'overview',
    label: 'Overview',
    items: [['today', 'Overview', Home]],
  },
  {
    id: 'assist',
    label: 'Assist',
    items: [
      ['agent', 'My Agent', Sparkles],
      ['telegram', 'Telegram', Send],
      ['inbox', 'Unified Inbox', Inbox],
    ],
  },
  {
    id: 'plan',
    label: 'Plan',
    items: [
      ['tasks', 'Tasks & Goals', ListTodo],
      ['calendar', 'Calendar', CalendarDays],
      ['growth', 'Personal Growth', Target],
      ['automation', 'Automation Studio', Workflow],
    ],
  },
  {
    id: 'knowledge',
    label: 'Knowledge',
    items: [
      ['memory', 'Memory', Brain],
      ['knowledge', 'Knowledge Hub', BookOpen],
    ],
  },
  {
    id: 'system',
    label: 'System',
    items: [
      ['connections', 'Integrations', Link2],
      ['activity', 'Activity & Logs', Activity],
      ['settings', 'Settings', Settings],
    ],
  },
];

export const navItems = navSections.flatMap((section) => section.items);

export const authRoutes = ['login', 'register', 'reset'];

export const validRoutes = [...authRoutes, ...navItems.map(([id]) => id), 'studio'];

export function pageTitle(page) {
  if (page === 'studio') return 'Automation Studio';
  return navItems.find((item) => item[0] === page)?.[1] || 'Overview';
}
