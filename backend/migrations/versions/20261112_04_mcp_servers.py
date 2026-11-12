"""Add mcp_servers (P9 / INT-MCP-01)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_04"
down_revision = "20261112_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)
    if offline or not inspector.has_table("mcp_servers"):
        op.create_table(
            "mcp_servers",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("transport", sa.String(16), nullable=False, server_default="stdio"),
            sa.Column("command", sa.Text(), server_default=""),
            sa.Column("url", sa.Text(), server_default=""),
            sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("read_only", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tool_allowlist", sa.JSON()),
            sa.Column("timeout_seconds", sa.Float(), nullable=False, server_default="15"),
            sa.Column("max_output_bytes", sa.Integer(), nullable=False, server_default="32768"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)
    if offline or (inspector is not None and inspector.has_table("mcp_servers")):
        op.drop_table("mcp_servers")
