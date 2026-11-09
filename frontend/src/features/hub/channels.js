/** Channel agents shown in the Personal Agent Hub sidebar. */

export const CHANNEL_GROUPS = [
  {
    id: 'messaging',
    label: 'Messaging',
    addLabel: 'Add channel',
    skills: true,
    icon: 'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  },
  {
    id: 'google',
    label: 'Google',
    addLabel: 'Add Google app',
    skills: true,
    icon: 'M12 3l8 4.5v9L12 21l-8-4.5v-9L12 3z',
  },
  {
    id: 'social',
    label: 'Social',
    addLabel: 'Add social',
    skills: true,
    icon: 'M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z',
  },
];

/**
 * live: channel has a real integration path in v1.
 * scaffold: UI only — Connect later / Coming soon, no fake metrics.
 */
export const CHANNELS = [
  {
    id: 'telegram',
    name: 'Telegram',
    fullName: 'Telegram Agent',
    color: 'bg-sky-500',
    group: 'messaging',
    live: true,
    description:
      'Chat with AURA in Telegram. Draft replies, triage chats, and run approved sends through Hermes.',
    capabilities: [
      { id: 'cap-tg-inbox', name: 'Inbox' },
      { id: 'cap-tg-replies', name: 'Replies' },
    ],
    plannedSkills: ['Draft reply', 'Summarize unread', 'Start / stop bot'],
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp',
    fullName: 'WhatsApp Agent',
    color: 'bg-emerald-500',
    group: 'messaging',
    live: false,
    description: 'Personal WhatsApp automation. Connection arrives in a later phase.',
    capabilities: [{ id: 'cap-wa-inbox', name: 'Inbox' }],
    plannedSkills: ['Draft reply', 'Label conversations'],
  },
  {
    id: 'gmail',
    name: 'Gmail',
    fullName: 'Gmail Agent',
    color: 'bg-rose-500',
    group: 'google',
    live: true,
    description: 'Read and draft mail with approval before send. Uses your Google OAuth client.',
    capabilities: [
      { id: 'cap-gm-inbox', name: 'Inbox' },
      { id: 'cap-gm-compose', name: 'Compose' },
    ],
    plannedSkills: ['Summarize inbox', 'Draft reply', 'Label thread'],
  },
  {
    id: 'calendar',
    name: 'Calendar',
    fullName: 'Google Calendar Agent',
    color: 'bg-blue-500',
    group: 'google',
    live: true,
    description: 'See upcoming events and draft calendar changes with approval.',
    capabilities: [
      { id: 'cap-cal-agenda', name: 'Agenda' },
      { id: 'cap-cal-schedule', name: 'Scheduling' },
    ],
    plannedSkills: ['List upcoming', 'Draft event', 'Find free time'],
  },
  {
    id: 'drive',
    name: 'Drive',
    fullName: 'Google Drive Agent',
    color: 'bg-amber-500',
    group: 'google',
    live: true,
    description: 'Find and summarize Drive files. Write actions require approval.',
    capabilities: [
      { id: 'cap-dr-search', name: 'Search' },
      { id: 'cap-dr-files', name: 'Files' },
    ],
    plannedSkills: ['Search files', 'Summarize document'],
  },
  {
    id: 'linkedin',
    name: 'LinkedIn',
    fullName: 'LinkedIn Agent',
    color: 'bg-indigo-600',
    group: 'social',
    live: false,
    description: 'Professional posts and outreach. Scaffold only in v1.',
    capabilities: [{ id: 'cap-li-content', name: 'Content' }],
    plannedSkills: ['Draft post', 'Schedule post'],
  },
  {
    id: 'x',
    name: 'X',
    fullName: 'X Agent',
    color: 'bg-slate-800',
    group: 'social',
    live: false,
    description: 'Posts and mentions on X. Scaffold only in v1.',
    capabilities: [{ id: 'cap-x-content', name: 'Content' }],
    plannedSkills: ['Draft post', 'Reply to mention'],
  },
  {
    id: 'instagram',
    name: 'Instagram',
    fullName: 'Instagram Agent',
    color: 'bg-pink-500',
    group: 'social',
    live: false,
    description: 'Captions and content planning. Scaffold only in v1.',
    capabilities: [{ id: 'cap-ig-content', name: 'Content' }],
    plannedSkills: ['Draft caption', 'Content calendar note'],
  },
  {
    id: 'facebook',
    name: 'Facebook',
    fullName: 'Facebook Agent',
    color: 'bg-blue-700',
    group: 'social',
    live: false,
    description: 'Page posts and planning. Scaffold only in v1.',
    capabilities: [{ id: 'cap-fb-content', name: 'Content' }],
    plannedSkills: ['Draft post'],
  },
  {
    id: 'youtube',
    name: 'YouTube',
    fullName: 'YouTube Agent',
    color: 'bg-red-600',
    group: 'social',
    live: false,
    description: 'Titles, descriptions, and upload planning. Scaffold only in v1.',
    capabilities: [{ id: 'cap-yt-content', name: 'Content' }],
    plannedSkills: ['Draft title', 'Draft description'],
  },
];

export const CHANNEL_TABS = [
  { id: 'skills', label: 'Skills' },
  { id: 'requests', label: 'Requests' },
  { id: 'board', label: 'Board' },
  { id: 'roadmap', label: 'Roadmap' },
];

export const WORKFLOW_STATUSES = [
  { id: 'draft', label: 'Draft', style: 'bg-slate-100 text-slate-700', dot: 'bg-slate-400' },
  { id: 'defined', label: 'Defined', style: 'bg-sky-100 text-sky-700', dot: 'bg-sky-500' },
  { id: 'building', label: 'In build', style: 'bg-amber-100 text-amber-800', dot: 'bg-amber-500' },
  { id: 'live', label: 'Live', style: 'bg-emerald-100 text-emerald-700', dot: 'bg-emerald-500' },
];

export const STAGES = [
  { id: 'backlog', label: 'Backlog' },
  { id: 'now', label: 'Now' },
  { id: 'next', label: 'Next' },
  { id: 'later', label: 'Later' },
  { id: 'shipped', label: 'Shipped' },
];

export function channelById(id) {
  return CHANNELS.find((c) => c.id === id) || null;
}

export function channelsInGroup(groupId) {
  return CHANNELS.filter((c) => c.group === groupId);
}

/** Default skills seeded into hub state for live channels. */
export function defaultSkills() {
  return [
    {
      id: 'sk-tg-draft',
      channelId: 'telegram',
      capabilityId: 'cap-tg-replies',
      name: 'Draft Telegram reply',
      status: 'live',
      humanControl: 'You approve before any send.',
      deliverables: 'Suggested reply text in chat.',
    },
    {
      id: 'sk-tg-bot',
      channelId: 'telegram',
      capabilityId: 'cap-tg-inbox',
      name: 'Bot runtime control',
      status: 'live',
      humanControl: 'Start/stop from the hub only.',
      deliverables: 'Bot listening state.',
    },
    {
      id: 'sk-gm-summary',
      channelId: 'gmail',
      capabilityId: 'cap-gm-inbox',
      name: 'Summarize Gmail inbox',
      status: 'defined',
      humanControl: 'Read-only until you connect Google.',
      deliverables: 'Inbox summary.',
    },
    {
      id: 'sk-gm-draft',
      channelId: 'gmail',
      capabilityId: 'cap-gm-compose',
      name: 'Draft Gmail reply',
      status: 'draft',
      humanControl: 'Approval required before send.',
      deliverables: 'Draft email body.',
    },
    {
      id: 'sk-cal-list',
      channelId: 'calendar',
      capabilityId: 'cap-cal-agenda',
      name: 'List upcoming events',
      status: 'defined',
      humanControl: 'Read-only calendar access.',
      deliverables: 'Agenda list.',
    },
    {
      id: 'sk-dr-search',
      channelId: 'drive',
      capabilityId: 'cap-dr-search',
      name: 'Search Drive files',
      status: 'defined',
      humanControl: 'Read-only Drive access.',
      deliverables: 'File matches.',
    },
  ];
}

export function defaultIdeas() {
  return [
    {
      id: 'idea-tg-triage',
      title: 'Telegram triage rules',
      description: 'Auto-label and prioritize chats once bot is stable.',
      channelId: 'telegram',
      stage: 'now',
      owner: 'You',
      reach: 1,
      impact: 2,
      confidence: 80,
      effort: 2,
      createdAt: new Date().toISOString().slice(0, 10),
    },
    {
      id: 'idea-gm-digest',
      title: 'Morning Gmail digest',
      description: 'Daily summary of unread important mail.',
      channelId: 'gmail',
      stage: 'next',
      owner: 'You',
      reach: 1,
      impact: 2,
      confidence: 70,
      effort: 3,
      createdAt: new Date().toISOString().slice(0, 10),
    },
    {
      id: 'idea-social-calendar',
      title: 'Cross-channel content calendar',
      description: 'One board for LinkedIn, X, Instagram once social connects.',
      channelId: 'linkedin',
      stage: 'later',
      owner: 'You',
      reach: 1,
      impact: 1,
      confidence: 50,
      effort: 5,
      createdAt: new Date().toISOString().slice(0, 10),
    },
  ];
}

export function defaultBoardNotes() {
  return [
    {
      id: 'note-welcome',
      channelId: null,
      text: 'Personal Agent Hub — plan automations here. Live channels: Telegram + Google.',
      x: 40,
      y: 40,
    },
  ];
}

export function riceScore(idea) {
  if (!idea.effort || idea.effort <= 0) return 0;
  return Math.round((idea.reach * idea.impact * (idea.confidence / 100)) / idea.effort);
}
