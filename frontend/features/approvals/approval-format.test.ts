import { describe, expect, it } from "vitest";
import type { RunEvent } from "../../lib/api/types";
import {
  approvalFields,
  approvalFromEvent,
  approvalTitle,
  expiryLabel,
  isExpired,
  riskLabel,
  riskTone,
} from "./approval-format";

describe("approval formatting", () => {
  it("uses plain titles and falls back to a readable tool name", () => {
    expect(approvalTitle("google_gmail_send")).toBe("Send email");
    expect(approvalTitle("publish_post")).toBe("Publish post");
  });

  it("lists the exact payload with friendly labels and flags long text", () => {
    const fields = approvalFields({
      to: "ana@example.com",
      subject: "Hi",
      body: "Hello there",
      empty: "",
      nested: { a: 1 },
    });
    expect(fields.map((f) => [f.label, f.value])).toEqual([
      ["To", "ana@example.com"],
      ["Subject", "Hi"],
      ["Body", "Hello there"],
      ["Nested", '{"a":1}'],
    ]);
    expect(fields.find((f) => f.key === "body")?.long).toBe(true);
  });

  it("counts down to expiry and reports expired approvals", () => {
    const now = Date.parse("2026-11-11T12:00:00Z");
    expect(expiryLabel("2026-11-12T11:59:00Z", now)).toBe("Expires in 23 h 59 min");
    expect(expiryLabel("2026-11-11T12:30:00Z", now)).toBe("Expires in 30 min");
    expect(expiryLabel("2026-11-11T12:00:20Z", now)).toBe("Expires in under a minute");
    expect(expiryLabel("2026-11-11T11:00:00Z", now)).toBe("Expired");
    expect(expiryLabel(null, now)).toBeNull();
    expect(isExpired({ expires_at: "2026-11-11T11:00:00Z" }, now)).toBe(true);
    expect(isExpired({ expires_at: null }, now)).toBe(false);
  });

  it("labels risk", () => {
    expect(riskLabel("high")).toBe("High risk");
    expect(riskTone("high")).toBe("warning");
    expect(riskTone("low")).toBe("neutral");
  });

  it("builds a card from an approval.required event and ignores other events", () => {
    const event: RunEvent = {
      seq: 3,
      run_id: "run-1",
      type: "approval.required",
      data: {
        approval_id: "a1",
        tool: "google_gmail_send",
        arguments: { to: "ana@example.com" },
        summary: "Send an email via Gmail",
        risk: "high",
        untrusted_content: true,
        arguments_hash: "abc",
        expires_at: "2026-11-12T12:00:00Z",
      },
    };
    expect(approvalFromEvent(event, "s1")).toMatchObject({
      id: "a1",
      run_id: "run-1",
      session_id: "s1",
      risk: "high",
      untrusted_content: true,
      status: "pending",
      actionable: true,
    });
    expect(approvalFromEvent({ ...event, type: "token" })).toBeNull();
    expect(approvalFromEvent({ ...event, data: {} })).toBeNull();
  });
});
