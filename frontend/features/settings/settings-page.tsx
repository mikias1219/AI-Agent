"use client";

import { useSearchParams } from "next/navigation";
import { PageFrame } from "@/components/ui/page-frame";
import { AgentSection } from "./agent-section";
import { AppearanceSection } from "./appearance-section";
import { DataSection } from "./data-section";
import { NotificationsSection } from "./notifications-section";
import { PermissionsSection } from "./permissions-section";
import { ProfileSection } from "./profile-section";
import { SecuritySection } from "./security-section";
import { SettingsSubnav, settingsSectionFromSearch } from "./settings-subnav";

/** One nav row; the shell header already names the page. */
export function SettingsPage() {
  const searchParams = useSearchParams();
  const section = settingsSectionFromSearch(searchParams.get("section"));

  return (
    <PageFrame width="chat">
      <SettingsSubnav value={section} />
      {section === "profile" ? <ProfileSection /> : null}
      {section === "security" ? <SecuritySection /> : null}
      {section === "notifications" ? <NotificationsSection /> : null}
      {section === "agent" ? <AgentSection /> : null}
      {section === "permissions" ? <PermissionsSection /> : null}
      {section === "appearance" ? <AppearanceSection /> : null}
      {section === "data" ? <DataSection /> : null}
    </PageFrame>
  );
}
