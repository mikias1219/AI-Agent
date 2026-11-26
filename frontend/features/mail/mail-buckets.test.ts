import { describe, expect, it } from "vitest";
import { bucketMessages } from "./mail-buckets";

describe("bucketMessages", () => {
  it("puts reply-seeking mail in needs_reply", () => {
    const buckets = bucketMessages([
      {
        id: "1",
        from: "Sara",
        subject: "Re: Thursday",
        snippet: "Are you free Thursday afternoon?",
        receivedAt: "2026-11-13T07:00:00Z",
      },
    ]);
    expect(buckets.find((b) => b.id === "needs_reply")?.messages).toHaveLength(1);
  });

  it("defaults unknown mail to FYI", () => {
    const buckets = bucketMessages([
      {
        id: "2",
        from: "News",
        subject: "Weekly digest",
        snippet: "Here is what happened.",
        receivedAt: "2026-11-13T07:00:00Z",
      },
    ]);
    expect(buckets.find((b) => b.id === "fyi")?.messages).toHaveLength(1);
  });

  it("does not invent messages when input is empty", () => {
    const buckets = bucketMessages([]);
    expect(buckets.every((b) => b.messages.length === 0)).toBe(true);
  });

  it("names filters for what they match, never as the agent's judgement", () => {
    const labels = bucketMessages([]).map((b) => b.label);
    expect(labels).toEqual(["Asks a question", "Follow-ups", "Everything else"]);
    expect(labels.join(" ")).not.toMatch(/Compass/i);
  });

  it("keeps a message that mentions a draft in a real filter", () => {
    const buckets = bucketMessages([
      {
        id: "3",
        from: "Dawit",
        subject: "Draft contract",
        snippet: "Could you look at this draft?",
        receivedAt: "2026-11-13T07:00:00Z",
      },
    ]);
    expect(buckets.find((b) => b.id === "needs_reply")?.messages).toHaveLength(1);
  });
});
