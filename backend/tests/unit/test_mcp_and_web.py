"""P9 MCP adapter + web tools offline tests."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.tools.builtins.web import web_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.exceptions import PermissionDeniedError
from personal_agent.domain.mcp import McpServer, McpTransport
from personal_agent.domain.models import ToolCall
from personal_agent.infrastructure.integrations.mcp.adapter import McpToolAdapter
from personal_agent.infrastructure.integrations.mcp.client import (
    FakeMcpClient,
    McpClientError,
    StdioMcpClient,
)
from personal_agent.infrastructure.persistence.repositories import ApprovalRepositoryImpl

ECHO_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "mcp_echo_server.py"


def test_fake_mcp_discover_and_call_through_registry(tool_registry, ctx):
    server = McpServer(
        id="echo1",
        name="Echo",
        transport=McpTransport.STDIO,
        command="unused",
        enabled=True,
        read_only=True,
    )
    fake = FakeMcpClient()
    adapter = McpToolAdapter(client_factory=lambda **_kwargs: fake)
    specs = adapter.discover(server)
    assert len(specs) == 1
    assert specs[0].access_kind == "read"
    tool_registry.register_all(specs)
    result = tool_registry.execute(
        ToolCall(id="1", name="mcp:echo1:echo", arguments={"message": "hi"}),
        ctx,
    )
    assert result.ok
    payload = json.loads(result.output)
    assert payload["untrusted"] is True
    assert payload["text"] == "hi"
    assert ctx.untrusted_content is True


def test_mcp_execute_requires_approval(tool_registry, ctx):
    server = McpServer(
        id="echo2",
        name="Echo",
        transport=McpTransport.STDIO,
        enabled=True,
        read_only=False,
    )
    adapter = McpToolAdapter(client_factory=lambda **_kwargs: FakeMcpClient())
    tool_registry.register_all(adapter.discover(server))
    with pytest.raises(PermissionDeniedError):
        tool_registry.execute(
            ToolCall(id="2", name="mcp:echo2:echo", arguments={"message": "x"}),
            ctx,
        )


def test_mcp_execute_runs_when_approved(session_factory, ctx, policy, audit_log):
    server = McpServer(
        id="echo3",
        name="Echo",
        transport=McpTransport.STDIO,
        enabled=True,
        read_only=False,
    )
    registry = ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
            notifier=lambda _p, _d: "approved",
        ),
        audit=audit_log,
    )
    adapter = McpToolAdapter(client_factory=lambda **_kwargs: FakeMcpClient())
    registry.register_all(adapter.discover(server))
    result = registry.execute(
        ToolCall(id="3", name="mcp:echo3:echo", arguments={"message": "ok"}),
        ctx,
    )
    assert result.ok
    assert json.loads(result.output)["text"] == "ok"


def test_mcp_timeout():
    def factory(**kwargs):
        # Simulate timeout by raising like StdioMcpClient would.
        raise McpClientError("MCP stdio timeout after 0.01s (tools/call).")

    adapter = McpToolAdapter(client_factory=factory)
    server = McpServer(id="t", name="t", transport=McpTransport.STDIO, enabled=True)
    assert adapter.discover(server) == []


def test_mcp_oversized_output_truncated():
    huge = "z" * 50_000
    client = FakeMcpClient(max_output_bytes=100, handler=lambda _n, _a: huge)
    text = client.call_tool("echo", {"message": "ignored"})
    assert text.endswith("…")
    assert len(text.encode("utf-8")) <= 100


def test_stdio_echo_server_roundtrip():
    import shlex
    import sys

    if not ECHO_SCRIPT.is_file():
        pytest.skip("echo server script missing")
    command = f"{shlex.quote(sys.executable)} -u {shlex.quote(str(ECHO_SCRIPT))}"
    client = StdioMcpClient(
        command,
        timeout_seconds=5.0,
        max_output_bytes=4096,
    )
    try:
        tools = client.list_tools()
        assert tools[0].name == "echo"
        assert client.call_tool("echo", {"message": "ping"}) == "ping"
    finally:
        client.close()


def test_web_fetch_denies_localhost():
    tools = {t.name: t for t in web_tools()}
    out = json.loads(tools["web_fetch"].handler(None, {"url": "http://127.0.0.1/secret"}))  # type: ignore[arg-type]
    assert "denied" in out["error"].lower()


def test_web_search_and_fetch_with_mock_http(ctx, tool_registry):
    def handler(request: httpx.Request) -> httpx.Response:
        if "duckduckgo" in str(request.url):
            html = '<a class="result__a" href="https://example.com">Example Result</a>'
            return httpx.Response(200, text=html)
        return httpx.Response(200, text="<html><body><p>Hello page</p></body></html>")

    http = httpx.Client(transport=httpx.MockTransport(handler))
    tool_registry.register_all(web_tools(http_client=http))
    search = tool_registry.execute(
        ToolCall(id="s", name="web_search", arguments={"query": "aura"}),
        ctx,
    )
    assert search.ok
    payload = json.loads(search.output)
    assert payload["untrusted"] is True
    assert payload["results"]
    fetch = tool_registry.execute(
        ToolCall(id="f", name="web_fetch", arguments={"url": "https://example.com/"}),
        ctx,
    )
    assert fetch.ok
    assert "Hello page" in json.loads(fetch.output)["text"]


def test_allowlist_filters_tools():
    server = McpServer(
        id="a",
        name="A",
        transport=McpTransport.STDIO,
        enabled=True,
        tool_allowlist=["other"],
    )
    adapter = McpToolAdapter(client_factory=lambda **_kwargs: FakeMcpClient())
    assert adapter.discover(server) == []
