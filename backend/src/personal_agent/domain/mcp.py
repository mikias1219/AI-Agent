"""MCP server configuration (INT-MCP-01)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from personal_agent.domain.url_safety import is_private_or_local_url


class McpTransport(StrEnum):
    STDIO = "stdio"
    HTTP = "http"  # Streamable HTTP JSON-RPC POST


class McpPolicyError(ValueError):
    """An MCP server configuration is not allowed on this deployment."""


@dataclass(frozen=True, slots=True)
class McpTransportPolicy:
    """Which MCP transports this deployment may open.

    A stdio server is a command run on the API host, and an HTTP server on a private
    address reaches the host's internal network. Both are fine on the owner's own
    machine and are refused on a hosted deployment unless explicitly enabled.
    """

    production: bool = False
    allow_stdio: bool = False

    def blocked_reason(self, transport: McpTransport | str, url: str = "") -> str | None:
        """Why this endpoint may not be opened, or None when it is allowed."""
        if not self.production:
            return None
        kind = transport.value if isinstance(transport, McpTransport) else str(transport)
        if kind == McpTransport.STDIO.value and not self.allow_stdio:
            return (
                "Local command (stdio) MCP servers are turned off on this deployment. "
                "Use an HTTP server, or set MCP_ALLOW_STDIO=1 on the API host."
            )
        if kind == McpTransport.HTTP.value and is_private_or_local_url(url):
            return "MCP server URLs must be public addresses on this deployment."
        return None

    def check(self, transport: McpTransport | str, url: str = "") -> None:
        reason = self.blocked_reason(transport, url)
        if reason:
            raise McpPolicyError(reason)


@dataclass(slots=True)
class McpServer:
    id: str
    name: str
    transport: McpTransport
    command: str = ""  # stdio: executable + args as shell-ish string
    url: str = ""  # http endpoint
    enabled: bool = True
    # When True, tools the server itself marks read-only run as `read`. Every other
    # tool still registers as `execute` and asks for approval.
    read_only: bool = False
    tool_allowlist: list[str] = field(default_factory=list)  # empty = all tools
    timeout_seconds: float = 15.0
    max_output_bytes: int = 32_768
    created_at: datetime | None = None
    updated_at: datetime | None = None
