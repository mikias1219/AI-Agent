import { describe, expect, it } from "vitest";
import type { GoogleMessage } from "@/lib/api/google";
import { askingCount, gmailLink } from "./mail-panel-logic";

const msg = (subject: string, snippet = ""): GoogleMessage => ({
  id: subject,
  from: "Abel <abel@example.com>",
  subject,
  snippet,
  receivedAt: "2026-11-27T08:00:00Z",
});

describe("mail panel helpers", () => {
  it("counts messages that ask you something", () => {
    expect(
      askingCount([msg("Can you review the PR?"), msg("Newsletter"), msg("RSVP by Friday")]),
    ).toBe(2);
    expect(askingCount([])).toBe(0);
  });

  it("links a message to Gmail", () => {
    expect(gmailLink("abc 123")).toBe("https://mail.google.com/mail/u/0/#all/abc%20123");
  });
});
