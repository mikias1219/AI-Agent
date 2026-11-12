"""MCP server configuration persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import sessionmaker

from personal_agent.domain.mcp import McpServer, McpTransport
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import McpServerRow


def _now() -> datetime:
    return datetime.now(UTC)


def _to_domain(row: McpServerRow) -> McpServer:
    return McpServer(
        id=row.id,
        name=row.name,
        transport=McpTransport(row.transport),
        command=row.command or "",
        url=row.url or "",
        enabled=bool(row.enabled),
        read_only=bool(row.read_only),
        tool_allowlist=list(row.tool_allowlist or []),
        timeout_seconds=float(row.timeout_seconds or 15.0),
        max_output_bytes=int(row.max_output_bytes or 32768),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class McpServerStoreImpl:
    def __init__(self, session_factory: sessionmaker) -> None:
        self._factory = session_factory

    def list(self) -> list[McpServer]:
        with session_scope(self._factory) as session:
            rows = session.query(McpServerRow).order_by(McpServerRow.name).all()
            return [_to_domain(row) for row in rows]

    def get(self, server_id: str) -> McpServer | None:
        with session_scope(self._factory) as session:
            row = session.get(McpServerRow, server_id)
            return _to_domain(row) if row else None

    def save(self, server: McpServer) -> None:
        with session_scope(self._factory) as session:
            row = session.get(McpServerRow, server.id)
            if row is None:
                row = McpServerRow(id=server.id)
                session.add(row)
                row.created_at = server.created_at or _now()
            row.name = server.name
            row.transport = server.transport.value
            row.command = server.command
            row.url = server.url
            row.enabled = 1 if server.enabled else 0
            row.read_only = 1 if server.read_only else 0
            row.tool_allowlist = list(server.tool_allowlist)
            row.timeout_seconds = server.timeout_seconds
            row.max_output_bytes = server.max_output_bytes
            row.updated_at = _now()

    def delete(self, server_id: str) -> None:
        with session_scope(self._factory) as session:
            row = session.get(McpServerRow, server_id)
            if row is not None:
                session.delete(row)
