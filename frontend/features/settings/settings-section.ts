export type SettingsSection =
  "profile" | "security" | "notifications" | "agent" | "permissions" | "appearance" | "data";

export const SETTINGS_SECTION_ITEMS: { id: SettingsSection; label: string }[] = [
  { id: "profile", label: "Profile" },
  { id: "security", label: "Security" },
  { id: "notifications", label: "Notifications" },
  { id: "agent", label: "Agent" },
  { id: "permissions", label: "Permissions" },
  { id: "appearance", label: "Appearance" },
  { id: "data", label: "Data" },
];

export const DEFAULT_SETTINGS_SECTION: SettingsSection = "profile";

/** Old links used "account" and "runtime"; keep them working. */
const LEGACY: Record<string, SettingsSection> = {
  account: "profile",
  runtime: "agent",
  password: "security",
  notification: "notifications",
};

export function isSettingsSection(value: string | null): value is SettingsSection {
  return SETTINGS_SECTION_ITEMS.some((item) => item.id === value);
}

export function normalizeSettingsSection(value: string | null): SettingsSection {
  if (isSettingsSection(value)) return value;
  return (value && LEGACY[value]) || DEFAULT_SETTINGS_SECTION;
}
