"use client";

import { Tabs } from "@/components/ui/tabs";

export type GoogleApp = "gmail" | "calendar" | "drive";

const ITEMS = [
  { id: "gmail", label: "Gmail" },
  { id: "calendar", label: "Calendar" },
  { id: "drive", label: "Drive" },
];

export type GoogleSubnavProps = {
  value: GoogleApp;
  onChange: (id: GoogleApp) => void;
};

export function GoogleSubnav({ value, onChange }: GoogleSubnavProps) {
  return <Tabs items={ITEMS} value={value} onChange={(id) => onChange(id as GoogleApp)} />;
}

export function isGoogleApp(value: string | null): value is GoogleApp {
  return value === "gmail" || value === "calendar" || value === "drive";
}
