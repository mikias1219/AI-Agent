export type SettingsSection = "account" | "appearance" | "runtime" | "permissions" | "data";

export const SETTINGS_SECTION_ITEMS: { id: SettingsSection; label: string }[] = [
  { id: "account", label: "Account" },
  { id: "appearance", label: "Appearance" },
  { id: "runtime", label: "Runtime" },
  { id: "permissions", label: "Permissions" },
  { id: "data", label: "Data" },
];

export function isSettingsSection(value: string | null): value is SettingsSection {
  return (
    value === "account" ||
    value === "appearance" ||
    value === "runtime" ||
    value === "permissions" ||
    value === "data"
  );
}

export const DEFAULT_SETTINGS_SECTION: SettingsSection = "account";
