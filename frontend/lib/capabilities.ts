export type CapabilityMode = "api" | "mock";

export const capabilities: {
  chat: CapabilityMode;
  tasks: CapabilityMode;
  activity: CapabilityMode;
  telegram: CapabilityMode;
  google: CapabilityMode;
  memory: CapabilityMode;
} = {
  chat: "api",
  tasks: "api",
  activity: "api",
  telegram: "api",
  google: "api",
  memory: "api",
};

export type CapabilityKey = keyof typeof capabilities;
