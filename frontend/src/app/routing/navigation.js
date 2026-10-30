import { Home, Sparkles, FileText, Link2, Clock3, Send, ListTodo } from 'lucide-react';
export const navItems = [
  ['today', 'Home', Home],
  ['agent', 'My agent', Sparkles],
  ['telegram', 'Telegram', Send],
  ['tasks', 'Tasks & approvals', ListTodo],
  ['studio', 'Content studio', FileText],
  ['connections', 'Connected apps', Link2],
  ['activity', 'Activity', Clock3],
];
export const authRoutes = ['login', 'register', 'reset'];
export const validRoutes = [...authRoutes, ...navItems.map(([id]) => id)];
