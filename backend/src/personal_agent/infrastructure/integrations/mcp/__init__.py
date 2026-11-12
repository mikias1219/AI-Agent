"""MCP client transports and tool adapter (INT-MCP-01)."""

from personal_agent.infrastructure.integrations.mcp.adapter import McpToolAdapter
from personal_agent.infrastructure.integrations.mcp.client import (
    FakeMcpClient,
    HttpMcpClient,
    McpClientError,
    McpToolInfo,
    StdioMcpClient,
    open_mcp_client,
)

__all__ = [
    "FakeMcpClient",
    "HttpMcpClient",
    "McpClientError",
    "McpToolAdapter",
    "McpToolInfo",
    "StdioMcpClient",
    "open_mcp_client",
]
