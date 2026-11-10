"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Tabs } from "@/components/ui/tabs";
import {
  DEFAULT_SETTINGS_SECTION,
  SETTINGS_SECTION_ITEMS,
  isSettingsSection,
  type SettingsSection,
} from "./settings-section";

export type SettingsSubnavProps = {
  value: SettingsSection;
};

export function SettingsSubnav({ value }: SettingsSubnavProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  function select(next: SettingsSection) {
    const params = new URLSearchParams(searchParams.toString());
    if (next === DEFAULT_SETTINGS_SECTION) {
      params.delete("section");
    } else {
      params.set("section", next);
    }
    const query = params.toString();
    router.replace(query ? `/settings?${query}` : "/settings", { scroll: false });
  }

  return (
    <Tabs
      items={SETTINGS_SECTION_ITEMS}
      value={value}
      onChange={(id) => select(id as SettingsSection)}
    />
  );
}

export function settingsSectionFromSearch(
  sectionParam: string | null,
): SettingsSection {
  return isSettingsSection(sectionParam) ? sectionParam : DEFAULT_SETTINGS_SECTION;
}
