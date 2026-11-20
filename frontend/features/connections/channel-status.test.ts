import { describe, expect, it } from "vitest";
import type { GoogleStatus } from "@/lib/api/google";
import type { McpServer } from "@/lib/api/mcp";
import { googleCard, mcpCard } from "./channel-status";

const google = (over: Partial<GoogleStatus>): GoogleStatus =>
  ({
    oauth_configured: true,
    connected: false,
    email: null,
    read_only: true,
    services: [],
    ...over,
  }) as GoogleStatus;

const server = (over: Partial<McpServer>): McpServer =>
  ({
    id: "s1",
    name: "docs",
    transport: "http",
    enabled: true,
    read_only: false,
    blocked_reason: null,
    ...over,
  }) as McpServer;

describe("connection cards report real state", () => {
  it("shows checking while loading and unavailable when the request failed", () => {
    expect(googleCard(undefined).badge).toBe("Checking");
    expect(googleCard(null).badge).toBe("Unavailable");
    expect(mcpCard(undefined).badge).toBe("Checking");
    expect(mcpCard(null).badge).toBe("Unavailable");
  });

  it("never describes Google as sample data", () => {
    const states = [
      googleCard(google({ oauth_configured: false })),
      googleCard(google({})),
      googleCard(google({ connected: true, email: "owner@example.com" })),
      googleCard(google({ connected: true, email: "owner@example.com", read_only: false })),
    ];
    expect(states.map((s) => s.badge)).toEqual([
      "Needs setup",
      "Not connected",
      "Connected",
      "Connected",
    ]);
    expect(states[2]?.description).toContain("owner@example.com");
    expect(states[2]?.description).toContain("Read-only");
    expect(states[3]?.description).toContain("ask you first");
    for (const state of states) expect(state.description).not.toMatch(/sample|preview/i);
  });

  it("counts MCP servers and flags the ones this deployment blocks", () => {
    expect(mcpCard([]).badge).toBe("None added");
    expect(mcpCard([server({}), server({ id: "s2", enabled: false })]).badge).toBe("1 active");
    const blocked = mcpCard([server({}), server({ id: "s2", blocked_reason: "stdio is off" })]);
    expect(blocked.badge).toBe("1 active");
    expect(blocked.tone).toBe("warning");
    expect(blocked.description).toContain("1 blocked");
  });
});
