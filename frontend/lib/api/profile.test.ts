import { describe, expect, it } from "vitest";
import {
  isEnforced,
  isEnforcedChild,
  passwordStrength,
  PHOTO_MAX_BYTES,
  validatePhoto,
} from "./profile";

describe("validatePhoto", () => {
  it("accepts png, jpeg and webp up to 1 MB", () => {
    for (const type of ["image/png", "image/jpeg", "image/webp"]) {
      expect(validatePhoto({ type, size: 1000 })).toBeNull();
    }
    expect(validatePhoto({ type: "image/png", size: PHOTO_MAX_BYTES })).toBeNull();
  });

  it("rejects other types, empty and oversized files", () => {
    expect(validatePhoto({ type: "image/gif", size: 10 })).toMatch(/PNG, JPEG or WebP/);
    expect(validatePhoto({ type: "application/pdf", size: 10 })).not.toBeNull();
    expect(validatePhoto({ type: "image/png", size: 0 })).toMatch(/empty/);
    expect(validatePhoto({ type: "image/png", size: PHOTO_MAX_BYTES + 1 })).toMatch(/1 MB/);
  });
});

describe("enforced keys", () => {
  it("matches exact and dotted children", () => {
    expect(isEnforced(["daily_briefing"], "daily_briefing")).toBe(true);
    expect(isEnforced(["channels.telegram"], "channels")).toBe(true);
    expect(isEnforced(["daily_briefing"], "reminders")).toBe(false);
    expect(isEnforcedChild(["channels"], "channels", "in_app")).toBe(true);
    expect(isEnforcedChild(["channels.telegram"], "channels", "in_app")).toBe(false);
  });
});

describe("passwordStrength", () => {
  it("flags short passwords and rates longer ones", () => {
    expect(passwordStrength("").score).toBe(0);
    expect(passwordStrength("short").label).toMatch(/Too short/);
    expect(passwordStrength("alllowercaseletters").score).toBe(1);
    expect(passwordStrength("Abcdefghijkl1234!").score).toBe(3);
  });
});
