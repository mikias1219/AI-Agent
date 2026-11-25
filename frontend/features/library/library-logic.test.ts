import { describe, expect, it } from "vitest";
import type { Note } from "@/lib/api/notes";
import {
  addTags,
  askAuraHref,
  dataUrlToBase64,
  formatBytes,
  groupDiaryByMonth,
  normaliseTag,
  previewText,
  resolveMime,
  storagePercent,
  todayIso,
  validateUpload,
} from "./library-logic";

function entry(date: string): Note {
  return {
    id: date,
    kind: "diary",
    title: "",
    body: "x",
    tags: [],
    mood: null,
    entry_date: date,
    pinned: false,
    created_at: `${date}T10:00:00Z`,
    updated_at: `${date}T10:00:00Z`,
  };
}

describe("tags", () => {
  it("normalises", () => {
    expect(normaliseTag("  #Work ")).toBe("work");
    expect(normaliseTag("a".repeat(50))).toHaveLength(30);
  });
  it("adds comma separated, dedupes and caps at 10", () => {
    expect(addTags(["a"], "b, A, ,c")).toEqual(["a", "b", "c"]);
    const many = Array.from({ length: 10 }, (_, i) => `t${i}`);
    expect(addTags(many, "extra")).toEqual(many);
  });
});

describe("uploads", () => {
  it("accepts allowed types and falls back to extension", () => {
    expect(validateUpload({ name: "a.png", type: "image/png", size: 10 })).toEqual({
      ok: true,
      mime: "image/png",
    });
    expect(resolveMime("notes.md", "")).toBe("text/markdown");
  });
  it("rejects svg, unknown, empty and oversized", () => {
    expect(validateUpload({ name: "a.svg", type: "image/svg+xml", size: 10 }).ok).toBe(false);
    expect(validateUpload({ name: "a.exe", type: "application/x-msdownload", size: 10 }).ok).toBe(
      false,
    );
    expect(validateUpload({ name: "a.txt", type: "text/plain", size: 0 }).ok).toBe(false);
    const big = validateUpload({ name: "a.pdf", type: "application/pdf", size: 6 * 1024 * 1024 });
    expect(big.ok).toBe(false);
  });
  it("strips data url prefix", () => {
    expect(dataUrlToBase64("data:image/png;base64,QUJD")).toBe("QUJD");
  });
});

describe("format helpers", () => {
  it("formats bytes", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2.0 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
  it("computes storage percent", () => {
    expect(storagePercent(0)).toBe(0);
    expect(storagePercent(100 * 1024 * 1024)).toBe(50);
    expect(storagePercent(999 * 1024 * 1024)).toBe(100);
  });
  it("previews markdown as plain text", () => {
    expect(previewText("# Title\n\n**bold** text")).toBe("Title bold text");
    expect(previewText("a".repeat(300), 10)).toBe(`${"a".repeat(10)}…`);
  });
  it("builds ask links and today", () => {
    expect(askAuraHref("Find my notes about x")).toBe("/chat?q=Find%20my%20notes%20about%20x");
    expect(todayIso(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});

describe("diary grouping", () => {
  it("groups by month keeping order", () => {
    const g = groupDiaryByMonth([entry("2026-11-03"), entry("2026-11-01"), entry("2026-10-30")]);
    expect(g.map((x) => [x.label, x.items.length])).toEqual([
      ["November 2026", 2],
      ["October 2026", 1],
    ]);
  });
});
