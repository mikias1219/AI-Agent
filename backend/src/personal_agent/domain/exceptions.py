"""Single error hierarchy for the whole application.

Every layer raises subclasses of these; adapters translate library-specific errors
into them at their boundary, so callers never need to know which SDK is underneath.
"""

from __future__ import annotations


class AgentError(Exception):
    """Base for all expected, handled application errors."""


class ConfigurationError(AgentError):
    """Invalid or missing settings (bad .env value, unreachable provider URL...)."""


class ProviderError(AgentError):
    """Model provider failed: connection, timeout, malformed response."""


class ToolError(AgentError):
    """Base for the controlled tool system."""


class UnknownToolError(ToolError):
    """The model requested a tool that is not registered."""


class ToolInputError(ToolError):
    """Arguments failed schema validation for the registered tool."""


class PermissionDeniedError(ToolError):
    """The permission policy explicitly blocked this tool."""


class ApprovalRequiredError(ToolError):
    """An action needs (or failed to receive) human approval before execution."""

    def __init__(self, tool_name: str, reason: str) -> None:
        super().__init__(f"Approval required for '{tool_name}': {reason}")
        self.tool_name = tool_name
        self.reason = reason


class StorageError(AgentError):
    """Persistence layer failure, without leaking DB vendor details."""
