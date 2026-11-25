export type CapabilityMode = "api" | "mock";

export const capabilities: {
  chat: CapabilityMode;
  tasks: CapabilityMode;
  activity: CapabilityMode;
  telegram: CapabilityMode;
  google: CapabilityMode;
  memory: CapabilityMode;
  automations: CapabilityMode;
  goals: CapabilityMode;
  inbox: CapabilityMode;
  agent_control: CapabilityMode;
  calendar: CapabilityMode;
  mail: CapabilityMode;
  notes_diary: CapabilityMode;
  files: CapabilityMode;
  learning: CapabilityMode;
  reading: CapabilityMode;
  profile_account: CapabilityMode;
  task_outcomes: CapabilityMode;
  days: CapabilityMode;
  drive_backup: CapabilityMode;
  calendar_sync: CapabilityMode;
  daily_wrapup: CapabilityMode;
} = {
  chat: "api",
  tasks: "api",
  activity: "api",
  telegram: "api",
  google: "api",
  memory: "api",
  automations: "api",
  goals: "api",
  inbox: "api",
  agent_control: "api",
  calendar: "api",
  mail: "api",
  notes_diary: "api",
  files: "api",
  learning: "api",
  reading: "api",
  profile_account: "api",
  task_outcomes: "api",
  days: "api",
  drive_backup: "api",
  calendar_sync: "api",
  daily_wrapup: "api",
};

export type CapabilityKey = keyof typeof capabilities;
