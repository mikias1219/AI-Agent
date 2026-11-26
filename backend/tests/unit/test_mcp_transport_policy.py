"""MCP transport rules, private-URL detection and the stdio child environment."""

from __future__ import annotations

import pytest

from personal_agent.domain.mcp import (
    McpPolicyError,
    McpServer,
    McpTransport,
    McpTransportPolicy,
)
from personal_agent.domain.url_safety import is_private_or_local_url
from personal_agent.infrastructure.integrations.mcp.adapter import McpToolAdapter
from personal_agent.infrastructure.integrations.mcp.client import (
    FakeMcpClient,
    McpToolInfo,
    _tool_infos,
    child_environment,
)


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:9000/mcp",
        "http://127.0.0.1/mcp",
        "http://[::1]/mcp",
        "http://10.1.2.3/mcp",
        "http://172.20.0.5/mcp",
        "http://192.168.1.10/mcp",
        "http://169.254.169.254/latest/meta-data",
        "http://metadata.google.internal/",
        "http://db.internal/mcp",
        "http://printer.local/mcp",
        "not a url",
        "",
    ],
)
def test_private_and_local_urls_are_detected(url):
    assert is_private_or_local_url(url)


@pytest.mark.parametrize("url", ["https://mcp.example.com/mcp", "https://8.8.8.8/mcp"])
def test_public_urls_are_not_flagged(url):
    assert not is_private_or_local_url(url)


def test_local_deployment_allows_stdio_and_localhost():
    policy = McpTransportPolicy(production=False)
    assert policy.blocked_reason(McpTransport.STDIO) is None
    assert policy.blocked_reason(McpTransport.HTTP, "http://127.0.0.1:9000/mcp") is None


def test_production_blocks_stdio_unless_enabled():
    blocked = McpTransportPolicy(production=True)
    assert "stdio" in (blocked.blocked_reason(McpTransport.STDIO) or "")
    with pytest.raises(McpPolicyError):
        blocked.check("stdio")
    enabled = McpTransportPolicy(production=True, allow_stdio=True)
    assert enabled.blocked_reason(McpTransport.STDIO) is None


def test_production_blocks_private_http_urls_only():
    policy = McpTransportPolicy(production=True)
    assert policy.blocked_reason(McpTransport.HTTP, "http://10.0.0.8/mcp")
    assert policy.blocked_reason(McpTransport.HTTP, "https://mcp.example.com/mcp") is None


def test_blocked_server_is_never_opened():
    opened: list[dict] = []

    def factory(**kwargs):
        opened.append(kwargs)
        return FakeMcpClient()

    adapter = McpToolAdapter(client_factory=factory, policy=McpTransportPolicy(production=True))
    server = McpServer(id="s", name="S", transport=McpTransport.STDIO, command="anything")
    assert adapter.blocked_reason(server)
    assert adapter.discover(server) == []
    assert opened == []


def test_tool_registered_before_a_policy_change_refuses_to_run():
    """A spec built while allowed must still refuse once the transport is blocked."""
    server = McpServer(id="s", name="S", transport=McpTransport.STDIO, command="anything")
    spec = McpToolAdapter(
        client_factory=lambda **_kwargs: FakeMcpClient(),
        policy=McpTransportPolicy(production=True),
    )._spec_for(server, "echo", "Echo", {"type": "object"})
    with pytest.raises(RuntimeError, match="stdio"):
        spec.handler(None, {"message": "x"})  # type: ignore[arg-type]


def test_read_only_hint_is_parsed_strictly():
    infos = _tool_infos(
        {
            "tools": [
                {"name": "search", "annotations": {"readOnlyHint": True}},
                {"name": "write", "annotations": {"readOnlyHint": False}},
                {"name": "truthy", "annotations": {"readOnlyHint": "yes"}},
                {"name": "plain"},
                {"description": "no name"},
            ]
        }
    )
    assert [(info.name, info.read_only_hint) for info in infos] == [
        ("search", True),
        ("write", False),
        ("truthy", False),
        ("plain", False),
    ]


def test_read_only_server_only_frees_tools_that_declare_read_only():
    tools = [
        McpToolInfo("search", "Search notes", {"type": "object"}, read_only_hint=True),
        McpToolInfo("delete_note", "Delete a note", {"type": "object"}),
    ]
    adapter = McpToolAdapter(client_factory=lambda **_kwargs: FakeMcpClient(tools))
    read_only = McpServer(id="n", name="Notes", transport=McpTransport.HTTP, read_only=True)
    kinds = {spec.name: spec.access_kind for spec in adapter.discover(read_only)}
    assert kinds == {"mcp_n_search": "read", "mcp_n_delete_note": "execute"}

    normal = McpServer(id="n", name="Notes", transport=McpTransport.HTTP, read_only=False)
    assert {spec.access_kind for spec in adapter.discover(normal)} == {"execute"}


def test_child_environment_drops_compass_secrets_and_keeps_the_rest():
    env = child_environment(
        {
            "PATH": "/usr/bin",
            "HOME": "/home/me",
            "NOTES_API_KEY": "kept-for-the-server",
            "DATABASE_URL": "postgresql://secret",
            "DASHBOARD_SECRET_KEY": "secret",
            "GOOGLE_CLIENT_SECRET": "secret",
            "TELEGRAM_BOT_TOKEN": "secret",
            "OPENAI_COMPAT_API_KEY": "secret",
        }
    )
    assert env == {
        "PATH": "/usr/bin",
        "HOME": "/home/me",
        "NOTES_API_KEY": "kept-for-the-server",
        "PYTHONUNBUFFERED": "1",
    }
