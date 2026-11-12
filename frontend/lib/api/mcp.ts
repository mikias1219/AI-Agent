import { api } from "./client";

export type McpServer = {
  id: string;
  name: string;
  transport: "stdio" | "http" | string;
  command: string;
  url: string;
  enabled: boolean;
  read_only: boolean;
  tool_allowlist: string[];
  timeout_seconds: number;
  max_output_bytes: number;
  registered_tools?: number;
};

export function listMcpServers() {
  return api<McpServer[]>("/mcp/servers");
}

export function createMcpServer(input: {
  name: string;
  transport: string;
  command?: string;
  url?: string;
  enabled?: boolean;
  read_only?: boolean;
  tool_allowlist?: string[];
}) {
  return api<McpServer>("/mcp/servers", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function patchMcpServer(
  id: string,
  input: Partial<{
    name: string;
    transport: string;
    command: string;
    url: string;
    enabled: boolean;
    read_only: boolean;
    tool_allowlist: string[];
  }>,
) {
  return api<McpServer>(`/mcp/servers/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteMcpServer(id: string) {
  return api<void>(`/mcp/servers/${id}`, { method: "DELETE" });
}

export function discoverMcpServer(id: string) {
  return api<{
    server_id: string;
    discovered: { name: string; access_kind: string }[];
    registered_tools: number;
  }>(`/mcp/servers/${id}/discover`, { method: "POST", body: "{}" });
}
