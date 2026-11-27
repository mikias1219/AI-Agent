import { describe, expect, it } from "vitest";
import type { LearnItem } from "@/lib/api/learn";
import {
  buildWordsPrompt,
  chatHref,
  formatDue,
  levelText,
  nextDueIso,
  orderReviewQueue,
  parseReferenceList,
  progressPercent,
  reviewKeyAction,
} from "./learn-logic";

function item(id: string, box: number, next: string): LearnItem {
  return {
    id,
    kind: "word",
    term: id,
    meaning: "",
    example: "",
    language: "en",
    topic: "",
    box,
    next_review_at: next,
    times_correct: 0,
    times_wrong: 0,
    created_at: next,
    updated_at: next,
  };
}

describe("orderReviewQueue", () => {
  it("orders by due time then box", () => {
    const out = orderReviewQueue([
      item("c", 1, "2026-01-02T00:00:00Z"),
      item("b", 3, "2026-01-01T00:00:00Z"),
      item("a", 0, "2026-01-01T00:00:00Z"),
    ]);
    expect(out.map((i) => i.id)).toEqual(["a", "b", "c"]);
  });
});

describe("reviewKeyAction", () => {
  it("maps keys by state", () => {
    expect(reviewKeyAction(" ", false)).toBe("reveal");
    expect(reviewKeyAction(" ", true)).toBeNull();
    expect(reviewKeyAction("1", false)).toBeNull();
    expect(reviewKeyAction("1", true)).toBe("again");
    expect(reviewKeyAction("2", true)).toBe("know");
    expect(reviewKeyAction("x", true)).toBeNull();
  });
});

describe("prompts", () => {
  it("builds the words prompt", () => {
    expect(buildWordsPrompt(5, " travel ", "English")).toBe(
      "Teach me 5 new English words about travel. For each give the meaning and one example sentence, then save them to my Learn list.",
    );
    expect(buildWordsPrompt(3, "", "Spanish")).toContain("3 new Spanish words.");
  });
  it("encodes chat href", () => {
    expect(chatHref("a b&c")).toBe("/chat?q=a%20b%26c");
  });
});

describe("levels and progress", () => {
  it("formats level text", () => {
    expect(levelText(3)).toBe("Level 3 of 5");
    expect(levelText(9)).toBe("Level 5 of 5");
  });
  it("computes percent", () => {
    expect(progressPercent(0.456)).toBe(46);
    expect(progressPercent(2)).toBe(100);
    expect(progressPercent(Number.NaN)).toBe(0);
  });
});

describe("parseReferenceList", () => {
  it("trims, drops blanks and consecutive duplicates", () => {
    expect(parseReferenceList("  John 1 \n\nJohn 1\nJohn 2\nJohn 1\r\n")).toEqual([
      "John 1",
      "John 2",
      "John 1",
    ]);
  });
  it("caps at 1500", () => {
    const text = Array.from({ length: 1600 }, (_, i) => `Ref ${i}`).join("\n");
    expect(parseReferenceList(text)).toHaveLength(1500);
  });
});

describe("due helpers", () => {
  const now = new Date("2026-01-01T00:00:00Z");
  it("formats due", () => {
    expect(formatDue("2025-12-31T00:00:00Z", now)).toBe("Due now");
    expect(formatDue("2026-01-01T00:30:00Z", now)).toBe("In 30 min");
    expect(formatDue("2026-01-04T00:00:00Z", now)).toBe("In 3 days");
  });
  it("finds next due", () => {
    expect(
      nextDueIso([item("a", 1, "2025-01-01T00:00:00Z"), item("b", 1, "2026-01-02T00:00:00Z")], now),
    ).toBe("2026-01-02T00:00:00.000Z");
    expect(nextDueIso([], now)).toBeNull();
  });
});

import { newWordsContext } from "./learn-logic";

describe("newWordsContext", () => {
  it("lists saved words once and asks for that many new ones", () => {
    const ctx = newWordsContext(["candid", "Thorough", "candid ", "thorough"], 3);
    expect(ctx).toContain("exactly 3 words");
    expect(ctx.match(/candid/gi)).toHaveLength(1);
    expect(ctx.match(/thorough/gi)).toHaveLength(1);
    expect(ctx).toContain("choose a replacement");
  });

  it("says nothing is saved when the list is empty", () => {
    expect(newWordsContext([], 5)).toContain("Nothing is saved yet.");
  });

  it("keeps the newest words when the list is too long", () => {
    const many = Array.from({ length: 1000 }, (_, i) => `word${i}`);
    const ctx = newWordsContext(many, 5);
    expect(ctx).toContain("word999");
    expect(ctx).not.toContain("word0,");
    expect(ctx.length).toBeLessThan(4000);
  });
});
