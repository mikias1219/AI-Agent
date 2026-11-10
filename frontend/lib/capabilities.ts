export const capabilities = {
  chat: "api",
  tasks: "api",
  activity: "api",
  telegram: "api",
  google: "api",
  linkedin: "mock",
  facebook: "mock",
} as const;

export type CapabilityMode = (typeof capabilities)[keyof typeof capabilities];
export type CapabilityKey = keyof typeof capabilities;
