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
};

export type CapabilityKey = keyof typeof capabilities;
