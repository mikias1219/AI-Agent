import { describe, expect, it } from "vitest";
import { ApiError } from "./client";
import { parseRunEvent, runsUnavailable, splitNdjson } from "./runs";

describe("splitNdjson", () => {
  it("returns complete lines and keeps the partial tail", () => {
    expect(splitNdjson('{"a":1}\n{"b":2}\n{"c"')).toEqual({
      lines: ['{"a":1}', '{"b":2}'],
      rest: '{"c"',
    });
  });

  it("skips blank keep-alive lines", () => {
    expect(splitNdjson('\n{"a":1}\n\n')).toEqual({ lines: ['{"a":1}'], rest: "" });
  });
});

describe("parseRunEvent", () => {
  it("parses a stream line", () => {
    const line = JSON.stringify({ seq: 2, run_id: "r", type: "token", data: { text: "x" } });
    expect(parseRunEvent(line)).toMatchObject({ seq: 2, type: "token" });
  });

  it("rejects lines that are not run events", () => {
    expect(() => parseRunEvent('{"hello":true}')).toThrow("unreadable");
  });
});

describe("runsUnavailable", () => {
  it("only flags missing endpoints so real errors surface", () => {
    expect(runsUnavailable(new ApiError("nope", 404))).toBe(true);
    expect(runsUnavailable(new ApiError("bad", 400))).toBe(false);
    expect(runsUnavailable(new Error("x"))).toBe(false);
  });
});
