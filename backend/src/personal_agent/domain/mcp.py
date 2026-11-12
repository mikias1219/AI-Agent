"""MCP server configuration (INT-MCP-01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class McpTransport(StrEnum):
    STDIO = "stdio"
    HTTP = "http"  # Streamable HTTP JSON-RPC POST


@dataclass(slots=True)
class McpServer:
    id: str
    name: str
    transport: McpTransport
    command: str = ""  # stdio: executable + args as shell-ish string
    url: str = ""  # http endpoint
    enabled: bool = True
    read_only: bool = False  # when True, discovered tools register as access_kind=read
    tool_allowlist: list[str] = field(default_factory=list)  # empty = all tools
    timeout_seconds: float = 15.0
    max_output_bytes: int = 32_768
    created_at: datetime | None = None
    updated_at: datetime | None = None
