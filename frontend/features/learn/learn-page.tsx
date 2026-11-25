"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Tabs } from "@/components/ui/tabs";
import { ReadingTab } from "./reading-tab";
import { TodayTab } from "./today-tab";
import { WordsTab } from "./words-tab";

const TABS = [
  { id: "today", label: "Today" },
  { id: "words", label: "Words" },
  { id: "reading", label: "Reading" },
];

export function LearnPage() {
  const router = useRouter();
  const params = useSearchParams();
  const raw = params.get("tab");
  const tab = TABS.some((t) => t.id === raw) ? (raw as string) : "today";

  return (
    <Tabs
      aria-label="Learn sections"
      items={TABS}
      value={tab}
      onChange={(id) => router.replace(`/learn?tab=${id}`, { scroll: false })}
      panels={{
        today: <TodayTab />,
        words: <WordsTab />,
        reading: <ReadingTab />,
      }}
    />
  );
}
