"""Thin MCP JSON-RPC clients for stdio and Streamable HTTP (no SDK dependency)."""

from __future__ import annotations

import contextlib
import json
import os
import shlex
import subprocess
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

PROTOCOL_VERSION = "2025-03-26"


class McpClientError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class McpToolInfo:
    name: str
    description: str
    input_schema: dict[str, Any]


class McpClient(Protocol):
    def list_tools(self) -> list[McpToolInfo]: ...

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> str: ...

    def close(self) -> None: ...


def _content_to_text(result: Mapping[str, Any], *, max_bytes: int) -> str:
    if result.get("isError"):
        raise McpClientError(_truncate(json.dumps(result), max_bytes))
    parts: list[str] = []
    for item in result.get("content") or []:
        if isinstance(item, dict) and item.get("type") == "text":
            parts.append(str(item.get("text") or ""))
        elif isinstance(item, dict):
            parts.append(json.dumps(item, ensure_ascii=False))
        else:
            parts.append(str(item))
    text = "\n".join(parts) if parts else json.dumps(result, ensure_ascii=False)
    return _truncate(text, max_bytes)


def _truncate(text: str, max_bytes: int) -> str:
    raw = text.encode("utf-8")
    if len(raw) <= max_bytes:
        return text
    ellipsis = "…".encode()
    budget = max(0, max_bytes - len(ellipsis))
    return raw[:budget].decode("utf-8", errors="ignore") + "…"


class FakeMcpClient:
    """In-process client for offline tests."""

    def __init__(
        self,
        tools: list[McpToolInfo] | None = None,
        *,
        handler: Callable[[str, Mapping[str, Any]], str] | None = None,
        delay: float = 0.0,
        max_output_bytes: int = 32_768,
    ) -> None:
        self._tools = tools or [
            McpToolInfo(
                name="echo",
                description="Echo arguments back as text.",
                input_schema={
                    "type": "object",
                    "properties": {"message": {"type": "string"}},
                    "required": ["message"],
                },
            )
        ]
        self._handler = handler
        self._delay = delay
        self._max_output_bytes = max_output_bytes

    def list_tools(self) -> list[McpToolInfo]:
        return list(self._tools)

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> str:
        if self._delay:
            time.sleep(self._delay)
        if self._handler is not None:
            return _truncate(self._handler(name, arguments), self._max_output_bytes)
        if name != "echo":
            raise McpClientError(f"Unknown tool: {name}")
        return _truncate(str(arguments.get("message", "")), self._max_output_bytes)

    def close(self) -> None:
        return None


class StdioMcpClient:
    """Newline-delimited JSON-RPC over a subprocess (MCP stdio transport)."""

    def __init__(
        self,
        command: str,
        *,
        timeout_seconds: float = 15.0,
        max_output_bytes: int = 32_768,
    ) -> None:
        if not command.strip():
            raise McpClientError("stdio MCP server requires a command.")
        self._timeout = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._id = 0
        self._lock = threading.Lock()
        args = shlex.split(command)
        # Force unbuffered stdio so newline-delimited JSON-RPC is readable promptly.
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        exe_name = Path(args[0]).name if args else ""
        if exe_name.startswith("python") and "-u" not in args:
            args = [args[0], "-u", *args[1:]]
        self._proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env,
        )
        try:
            self._request(
                "initialize",
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "aura", "version": "0.1.0"},
                },
            )
            self._notify("notifications/initialized", {})
        except Exception:
            self.close()
            raise

    def list_tools(self) -> list[McpToolInfo]:
        result = self._request("tools/list", {})
        return [
            McpToolInfo(
                name=str(tool.get("name") or ""),
                description=str(tool.get("description") or ""),
                input_schema=dict(tool.get("inputSchema") or {"type": "object"}),
            )
            for tool in (result.get("tools") or [])
            if tool.get("name")
        ]

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> str:
        result = self._request("tools/call", {"name": name, "arguments": dict(arguments)})
        return _content_to_text(result, max_bytes=self._max_output_bytes)

    def close(self) -> None:
        if self._proc.poll() is not None:
            return
        with contextlib.suppress(Exception):
            if self._proc.stdin:
                self._proc.stdin.close()
        try:
            self._proc.terminate()
            self._proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(Exception):
                self._proc.kill()
        except Exception:  # noqa: BLE001 — sandbox may deny signals
            pass

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        payload = {"jsonrpc": "2.0", "method": method, "params": params}
        self._write(payload)

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            req_id = self._next_id()
            self._write({"jsonrpc": "2.0", "id": req_id, "method": method, "params": params})
            deadline = time.monotonic() + self._timeout
            while time.monotonic() < deadline:
                line = self._readline(deadline - time.monotonic())
                if line is None:
                    break
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if message.get("id") != req_id:
                    continue
                if "error" in message:
                    raise McpClientError(str(message["error"]))
                result = message.get("result")
                if not isinstance(result, dict):
                    raise McpClientError("MCP response missing result object.")
                return result
            raise McpClientError(f"MCP stdio timeout after {self._timeout}s ({method}).")

    def _write(self, payload: dict[str, Any]) -> None:
        if not self._proc.stdin:
            raise McpClientError("MCP process stdin is closed.")
        self._proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        self._proc.stdin.flush()

    def _readline(self, timeout: float) -> str | None:
        if not self._proc.stdout:
            return None
        bucket: list[str | None] = [None]

        def reader() -> None:
            try:
                bucket[0] = self._proc.stdout.readline() if self._proc.stdout else None
            except Exception:  # noqa: BLE001
                bucket[0] = None

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        thread.join(timeout=max(0.05, timeout))
        if thread.is_alive():
            return None
        line = bucket[0]
        return line.strip() if line else None


class HttpMcpClient:
    """Streamable HTTP: JSON-RPC POST to a single MCP endpoint."""

    def __init__(
        self,
        url: str,
        *,
        timeout_seconds: float = 15.0,
        max_output_bytes: int = 32_768,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not url.strip():
            raise McpClientError("HTTP MCP server requires a url.")
        self._url = url.strip()
        self._timeout = timeout_seconds
        self._max_output_bytes = max_output_bytes
        self._http = http_client or httpx.Client(timeout=timeout_seconds)
        self._owns = http_client is None
        self._id = 0
        self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "aura", "version": "0.1.0"},
            },
        )
        self._notify("notifications/initialized", {})

    def list_tools(self) -> list[McpToolInfo]:
        result = self._request("tools/list", {})
        return [
            McpToolInfo(
                name=str(tool.get("name") or ""),
                description=str(tool.get("description") or ""),
                input_schema=dict(tool.get("inputSchema") or {"type": "object"}),
            )
            for tool in (result.get("tools") or [])
            if tool.get("name")
        ]

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> str:
        result = self._request("tools/call", {"name": name, "arguments": dict(arguments)})
        return _content_to_text(result, max_bytes=self._max_output_bytes)

    def close(self) -> None:
        if self._owns:
            self._http.close()

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def _notify(self, method: str, params: dict[str, Any]) -> None:
        self._http.post(
            self._url,
            json={"jsonrpc": "2.0", "method": method, "params": params},
            headers={"Accept": "application/json, text/event-stream"},
        )

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        req_id = self._next_id()
        response = self._http.post(
            self._url,
            json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": params},
            headers={"Accept": "application/json, text/event-stream"},
            timeout=self._timeout,
        )
        if response.status_code >= 400:
            raise McpClientError(f"MCP HTTP {response.status_code} for {method}.")
        content_type = response.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            message = _parse_sse_json(response.text)
        else:
            message = response.json()
        if not isinstance(message, dict):
            raise McpClientError("MCP HTTP returned non-object JSON.")
        if "error" in message:
            raise McpClientError(str(message["error"]))
        result = message.get("result")
        if not isinstance(result, dict):
            raise McpClientError("MCP HTTP response missing result object.")
        return result


def _parse_sse_json(body: str) -> dict[str, Any]:
    for line in body.splitlines():
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload:
                data = json.loads(payload)
                if isinstance(data, dict):
                    return data
    raise McpClientError("MCP SSE stream contained no JSON data event.")


def open_mcp_client(
    *,
    transport: str,
    command: str = "",
    url: str = "",
    timeout_seconds: float = 15.0,
    max_output_bytes: int = 32_768,
    http_client: httpx.Client | None = None,
) -> McpClient:
    if transport == "stdio":
        return StdioMcpClient(
            command, timeout_seconds=timeout_seconds, max_output_bytes=max_output_bytes
        )
    if transport == "http":
        return HttpMcpClient(
            url,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
            http_client=http_client,
        )
    raise McpClientError(f"Unsupported MCP transport: {transport}")
