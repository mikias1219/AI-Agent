import { describe, expect, it } from "vitest";
import {
  calendarPendingWords,
  drivePendingWords,
  modeLine,
  runMessage,
  syncChip,
} from "./sync-logic";

const include = {
  notes: true,
  diary: true,
  daily: true,
  files: false,
  learning: true,
  reading: false,
};

describe("sync logic", () => {
  it("words pending counts only for included areas", () => {
    expect(
      drivePendingWords({
        include,
        pending: { notes: 2, diary: 1, daily: 0, files: 5, learning: true, reading: true },
      }),
    ).toEqual(["2 notes", "1 diary entry", "learning words"]);
    expect(calendarPendingWords(1)).toBe("1 task");
    expect(calendarPendingWords(0)).toBe("");
  });
  it("explains the mode", () => {
    expect(modeLine("ask", "backup")).toBe("Compass asks you first for each backup.");
    expect(modeLine("auto", "backup")).toBe("Automatic: you allowed this in Permissions.");
  });
  it("chooses an honest chip", () => {
    const base = { connected: true, scope_granted: true, enabled: true, last_error: null };
    expect(syncChip({ ...base, connected: false }).label).toBe("Google not connected");
    expect(syncChip({ ...base, scope_granted: false }).label).toBe("Needs reconnect");
    expect(syncChip({ ...base, last_error: "x" }).tone).toBe("danger");
    expect(syncChip(base).label).toBe("On");
    expect(syncChip({ ...base, enabled: false }).label).toBe("Off");
  });
  it("only reports what the API said", () => {
    expect(runMessage({ status: "awaiting_approval", approval_id: "a", summary: null })).toBe(
      "Waiting for your OK in Needs you",
    );
    expect(runMessage({ status: "nothing_to_do", approval_id: null, summary: null })).toMatch(
      /Nothing/,
    );
    expect(
      runMessage({
        status: "done",
        approval_id: null,
        summary: { created: 2, updated: 0, skipped: 1, failed: 0 },
      }),
    ).toBe("Done: 2 created, 1 unchanged.");
  });
});
