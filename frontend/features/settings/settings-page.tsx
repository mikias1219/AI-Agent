"use client";

import { useSearchParams } from "next/navigation";
import { AccountSection } from "./account-section";
import { AppearanceSection } from "./appearance-section";
import { DataSection } from "./data-section";
import { PermissionsSection } from "./permissions-section";
import { RuntimeSection } from "./runtime-section";
import { SettingsSubnav, settingsSectionFromSearch } from "./settings-subnav";
import type { SettingsSection } from "./settings-section";

const SECTION_HEADINGS: Record<SettingsSection, { title: string; description: string }> = {
  account: {
    title: "Account",
    description: "Signed-in workspace owner from auth.",
  },
  appearance: {
    title: "Appearance",
    description: "Global design tokens for the AURA shell.",
  },
  runtime: {
    title: "Runtime",
    description: "Model and integration status from the agent.",
  },
  permissions: {
    title: "Permissions",
    description: "What the UI and agent may access.",
  },
  data: {
    title: "Data",
    description: "Forget memories and other owner data controls.",
  },
};

export function SettingsPage() {
  const searchParams = useSearchParams();
  const section = settingsSectionFromSearch(searchParams.get("section"));
  const heading = SECTION_HEADINGS[section];

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5">
      <header>
        <p className="text-xs font-medium tracking-wide text-[var(--muted)] uppercase">Settings</p>
        <h1
          className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]"
          style={{ fontFamily: "var(--font-display)" }}
        >
          {heading.title}
        </h1>
        <p className="mt-2 max-w-xl text-sm text-[var(--muted)]">{heading.description}</p>
      </header>

      <SettingsSubnav value={section} />

      {section === "account" ? <AccountSection /> : null}
      {section === "appearance" ? <AppearanceSection /> : null}
      {section === "runtime" ? <RuntimeSection /> : null}
      {section === "permissions" ? <PermissionsSection /> : null}
      {section === "data" ? <DataSection /> : null}
    </div>
  );
}
