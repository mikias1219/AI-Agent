# AURA Phase 1 / P9 — MCP client and web tools

**Date:** 2026-11-12  
**Status:** In progress  
**Source:** `docs/AURA_PROPOSAL.md` Part 3 **P9** (INT-MCP-01, INT-WEB-01; BR-04)

## Goal

Configure MCP servers (stdio + Streamable HTTP), discover tools, register them in ToolRegistry with per-server allowlist, timeout, output size cap, and untrusted labeling. Default `access_kind` is `execute` unless the owner marks a tool read-only. Add web search and page fetch as read tools with a domain deny list. Ship a tiny local echo MCP server for tests/demo. Connections UI for MCP servers.

## Spec note

MCP protocol revision targeted: **2025-03-26 / Streamable HTTP** for HTTP transport (JSON-RPC POST to a single endpoint; accept `application/json` and `text/event-stream`). Stdio remains newline-delimited JSON-RPC (`initialize` → `tools/list` → `tools/call`). Implementation is a thin in-repo adapter (no mandatory third-party MCP SDK) so CI stays offline.

## Scope

- Table `mcp_servers` + Alembic migration (SQLite/Postgres)
- Domain + `McpServerStore` port; infrastructure stdio + HTTP transports
- `McpToolAdapter`: discover → `ToolSpec`s named `mcp:{server}:{tool}`; gate via registry
- Defaults: timeout (e.g. 15s), max output (e.g. 32 KiB), untrusted_output=True, access_kind=execute (or read when owner flags tool/server read-only)
- `/api/mcp/servers` CRUD + refresh/discover
- Connections → MCP page (list, enable, allowlist, transport fields)
- Echo MCP server script under `backend/scripts/mcp_echo_server.py`
- `web_search` + `web_fetch` read tools; deny list; size limits; untrusted
- Tests: discovery, execute requires approval, timeout, oversized truncate/error

## Out of scope

- INT-MCP-02 exposing AURA as an MCP server
- P10 evals / OTel

## Decisions

1. **No hard SDK dependency** for v1 — JSON-RPC client we own; swap later if needed.
2. **Registration timing:** refresh on API create/update/enable and at container build for enabled servers (stdio may be skipped if command missing; HTTP probed lazily on first use in tests via FakeTransport).
3. **Web search:** httpx GET against a configurable search URL template (default DuckDuckGo HTML lite); tests inject transport. Fetch uses httpx with deny list (`localhost`, link-local, metadata IPs).
