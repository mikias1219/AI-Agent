import { describe, expect, it } from "vitest";
import { decodeSnippet, parseSender } from "./mail-logic";

describe("mail logic", () => {
  it("decodes escaped snippets to plain text without producing markup", () => {
    expect(decodeSnippet("Don&#39;t &amp; won&#39;t &lt;b&gt;")).toBe("Don't & won't <b>");
    expect(decodeSnippet("&#128512;")).toBe("😀");
    expect(decodeSnippet("&#0;")).toBe("&#0;");
  });

  it("splits a From header into name and address", () => {
    expect(parseSender('"Ana Lee" <ana@example.com>')).toEqual({
      name: "Ana Lee",
      address: "ana@example.com",
    });
    expect(parseSender("<ana@example.com>")).toEqual({
      name: "ana@example.com",
      address: "ana@example.com",
    });
    expect(parseSender("ana@example.com")).toEqual({
      name: "ana@example.com",
      address: "ana@example.com",
    });
    expect(parseSender("")).toEqual({ name: "", address: "" });
  });
});
