# ADR 0009 — MCP client without a hard SDK dependency

## Status

Accepted

## Context

P9 needs MCP stdio and Streamable HTTP tool discovery/call behind ToolRegistry, plus offline CI. Pulling an evolving official SDK would couple packaging and make hermetic tests harder.

## Decision

- Implement a thin JSON-RPC client for **stdio** (newline-delimited) and **Streamable HTTP** (POST; accept JSON or SSE `data:` events), targeting protocol version `2025-03-26`.
- Persist servers in `mcp_servers`; `McpToolAdapter` registers `mcp:{server_id}:{tool}` ToolSpecs with allowlist, timeout, output size cap, untrusted labeling, and default `execute` (or `read` when the server is marked read-only).
- Ship `scripts/mcp_echo_server.py` for local demo/tests.
- Add `web_search` / `web_fetch` as read tools with host deny list and untrusted envelopes.

## Consequences

- Tests stay offline with FakeMcpClient / MockTransport; optional stdio echo subprocess proves the wire format.
- An official SDK can replace the transport layer later without changing ToolRegistry callers.
