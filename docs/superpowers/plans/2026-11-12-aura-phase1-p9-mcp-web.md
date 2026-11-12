# P9 MCP + Web Implementation Plan

> **For agentic workers:** Implement all tasks; commit per logical slice. Isolated worktree.

**Goal:** MCP server CRUD + tool adapter behind ToolRegistry; web_search/web_fetch; Connections UI; echo server for tests.

**Architecture:** mcp_servers persistence → McpToolAdapter registers ToolSpecs → registry gate; thin JSON-RPC stdio/HTTP transports; web tools as builtins.

**Tech Stack:** httpx, subprocess stdio, SQLAlchemy/Alembic, Next.js Connections, pytest mocks.

## Global Constraints

- Spec + proposal P9; BR-04 untrusted; offline tests; ToolRegistry only
- Do not build P10–P11 here

### Task 1: Schema + MCP transports + echo server

- [x] Migration mcp_servers; domain + store
- [x] Stdio + Streamable HTTP JSON-RPC client; echo server script
- [x] Tests: list/call echo; timeout; size cap

### Task 2: Registry adapter + web tools + API

- [x] McpToolAdapter → ToolSpecs; allowlist; read-only flag → access_kind
- [x] web_search / web_fetch; deny list
- [x] /api/mcp/servers CRUD + discover; wire container

### Task 3: Connections UI + docs

- [x] MCP connections page; nav from Connections
- [x] ADR + README + mark Implemented
