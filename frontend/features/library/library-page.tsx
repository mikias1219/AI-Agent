"use client";

import { useCallback } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Tabs } from "@/components/ui/tabs";
import { ModuleAgent } from "@/features/module-agent/module-agent";
import { DiaryTab } from "./diary-tab";
import { FilesTab } from "./files-tab";
import { NotesTab } from "./notes-tab";

const TABS = [
  { id: "notes", label: "Notes" },
  { id: "diary", label: "Diary" },
  { id: "files", label: "Files" },
];

export function LibraryPage() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const raw = params.get("tab");
  const tab = TABS.some((t) => t.id === raw) ? (raw as string) : "notes";

  const change = useCallback(
    (id: string) => router.replace(`${pathname}?tab=${id}`, { scroll: false }),
    [router, pathname],
  );

  return (
    <div className="flex flex-col gap-4">
      <ModuleAgent
        module="library"
        onDataChanged={() => window.dispatchEvent(new Event("compass:data-changed"))}
      />
      <Tabs items={TABS} value={tab} onChange={change} aria-label="Library sections" />
      {tab === "notes" ? <NotesTab /> : tab === "diary" ? <DiaryTab /> : <FilesTab />}
    </div>
  );
}
